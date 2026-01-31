from datetime import datetime

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app import db
from app.models import (
    Cutter,
    Installation,
    Machine,
    RemovalReason,
    Resharpening,
    ScrapReason,
    ToolPost,
)


def _days_between(start, end=None):
    if not start:
        return "—"
    end_time = end or datetime.utcnow()
    delta = end_time.date() - start.date()
    return max(delta.days, 0)


def _location_label(cutter):
    if cutter.location_type == "machine" and cutter.location_machine_id:
        machine = Machine.query.get(cutter.location_machine_id)
        tool_post = None
        if cutter.location_tool_post_id:
            tool_post = ToolPost.query.get(cutter.location_tool_post_id)
        parts = ["На станке"]
        if machine:
            parts.append(machine.name)
        if tool_post:
            parts.append(tool_post.name)
        return " — ".join(parts)
    if cutter.location_type == "warehouse":
        return "Склад"
    if cutter.location_type == "awaiting_resharpen":
        return "Ожидает переточку"
    if cutter.location_type == "in_resharpen":
        return "На переточке"
    if cutter.location_type == "scrapped":
        return "Списан"
    return cutter.location_type or "—"


def register_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for("cutters"))

    @app.route("/cutters")
    def cutters():
        query = Cutter.query
        search = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip()
        if search:
            query = query.filter(Cutter.serial_short.ilike(f"%{search}%"))
        if status:
            query = query.filter(Cutter.status == status)
        cutters_list = query.order_by(Cutter.serial_short.asc()).all()
        return render_template(
            "cutters.html",
            cutters=cutters_list,
            status=status,
            search=search,
            location_label=_location_label,
        )

    @app.route("/cutters/<int:cutter_id>")
    def cutter_detail(cutter_id):
        cutter = Cutter.query.get_or_404(cutter_id)
        installations = (
            Installation.query.filter_by(cutter_id=cutter.id)
            .order_by(Installation.installed_at.desc())
            .all()
        )
        resharpenings = (
            Resharpening.query.filter_by(cutter_id=cutter.id)
            .order_by(Resharpening.sharpened_at.desc())
            .all()
        )
        return render_template(
            "cutter_detail.html",
            cutter=cutter,
            installations=installations,
            resharpenings=resharpenings,
            days_between=_days_between,
            location_label=_location_label,
        )

    @app.route("/cutters/<int:cutter_id>/scrap", methods=["POST"])
    def scrap_cutter(cutter_id):
        cutter = Cutter.query.get_or_404(cutter_id)
        active_installation = Installation.query.filter_by(
            cutter_id=cutter.id,
            removed_at=None,
        ).first()
        if active_installation:
            flash("Нельзя списать резец, пока он установлен на станке.", "error")
            return redirect(url_for("cutter_detail", cutter_id=cutter.id))

        reason_name = request.form.get("scrap_reason", "").strip() or "Не указано"
        reason_code = reason_name.lower().replace(" ", "_")
        reason = ScrapReason.query.filter_by(code=reason_code).first()
        if not reason:
            reason = ScrapReason(code=reason_code, name=reason_name)
            db.session.add(reason)
            db.session.flush()

        cutter.status = "scrapped"
        cutter.location_type = "scrapped"
        cutter.scrapped_at = datetime.utcnow()
        cutter.scrap_reason_id = reason.id
        cutter.location_machine_id = None
        cutter.location_tool_post_id = None
        cutter.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Резец списан.", "success")
        return redirect(url_for("cutter_detail", cutter_id=cutter.id))

    @app.route("/cutters/<int:cutter_id>/resharpen", methods=["POST"])
    def resharpen_cutter(cutter_id):
        cutter = Cutter.query.get_or_404(cutter_id)
        radius_before = request.form.get("radius_before")
        radius_after = request.form.get("radius_after")
        comment = request.form.get("comment")
        if not radius_before or not radius_after:
            flash("Нужно указать радиусы до и после.", "error")
            return redirect(url_for("cutter_detail", cutter_id=cutter.id))

        resharpening = Resharpening(
            cutter_id=cutter.id,
            radius_before=radius_before,
            radius_after=radius_after,
            comment=comment,
        )
        cutter.radius_current = radius_after
        cutter.resharpen_count += 1
        cutter.updated_at = datetime.utcnow()
        db.session.add(resharpening)
        db.session.commit()
        flash("Переточка добавлена.", "success")
        return redirect(url_for("cutter_detail", cutter_id=cutter.id))

    @app.route("/machines")
    def machines():
        machines_list = Machine.query.order_by(Machine.name.asc()).all()
        active_installations = Installation.query.filter_by(removed_at=None).all()
        current_by_tool_post = {inst.tool_post_id: inst for inst in active_installations}
        available_cutters = Cutter.query.filter(
            Cutter.status.notin_(["in_work", "scrapped"])
        ).order_by(Cutter.serial_short.asc())
        return render_template(
            "machines.html",
            machines=machines_list,
            current_by_tool_post=current_by_tool_post,
            available_cutters=available_cutters,
            days_between=_days_between,
        )

    @app.route("/installations/replace", methods=["POST"])
    def replace_cutter():
        tool_post_id = request.form.get("tool_post_id", type=int)
        new_cutter_id = request.form.get("cutter_id", type=int)
        if not tool_post_id or not new_cutter_id:
            flash("Нужно выбрать tool post и резец.", "error")
            return redirect(url_for("machines"))

        tool_post = ToolPost.query.get_or_404(tool_post_id)
        new_cutter = Cutter.query.get_or_404(new_cutter_id)

        if new_cutter.status in {"in_work", "scrapped"}:
            flash("Резец недоступен для установки.", "error")
            return redirect(url_for("machines"))

        active_installation = Installation.query.filter_by(
            tool_post_id=tool_post.id,
            removed_at=None,
        ).first()
        if active_installation:
            active_installation.removed_at = datetime.utcnow()
            active_installation.comment = "Снят при замене"
            removed_cutter = active_installation.cutter
            removed_cutter.status = "warehouse"
            removed_cutter.location_type = "warehouse"
            removed_cutter.location_machine_id = None
            removed_cutter.location_tool_post_id = None
            removed_cutter.updated_at = datetime.utcnow()

        new_installation = Installation(
            cutter_id=new_cutter.id,
            machine_id=tool_post.machine_id,
            tool_post_id=tool_post.id,
            installed_at=datetime.utcnow(),
        )
        new_cutter.status = "in_work"
        new_cutter.location_type = "machine"
        new_cutter.location_machine_id = tool_post.machine_id
        new_cutter.location_tool_post_id = tool_post.id
        new_cutter.updated_at = datetime.utcnow()

        db.session.add(new_installation)
        db.session.commit()
        flash("Резец установлен.", "success")
        return redirect(url_for("machines"))

    @app.route("/seed", methods=["POST"])
    def seed_data():
        if Machine.query.first():
            flash("Данные уже загружены.", "info")
            return redirect(url_for("cutters"))

        machine = Machine(name="Станок 1", code="M1")
        tool_post_1 = ToolPost(machine=machine, name="T1", position=1)
        tool_post_2 = ToolPost(machine=machine, name="T2", position=2)

        cutter_a = Cutter(
            serial_full="CUT-0001-2024",
            serial_short="C-001",
            commissioned_at=datetime.utcnow(),
            status="warehouse",
            radius_current=5.0,
            resharpen_count=0,
            location_type="warehouse",
        )
        cutter_b = Cutter(
            serial_full="CUT-0002-2024",
            serial_short="C-002",
            commissioned_at=datetime.utcnow(),
            status="warehouse",
            radius_current=4.5,
            resharpen_count=1,
            location_type="warehouse",
        )

        db.session.add_all([machine, tool_post_1, tool_post_2, cutter_a, cutter_b])
        db.session.commit()
        flash("Тестовые данные созданы.", "success")
        return redirect(url_for("cutters"))
