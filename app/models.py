from datetime import datetime

from app import db


class Cutter(db.Model):
    __tablename__ = "cutters"

    id = db.Column(db.Integer, primary_key=True)
    serial_full = db.Column(db.String(128), unique=True, nullable=False)
    serial_short = db.Column(db.String(64), unique=True, nullable=False)
    commissioned_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(32), nullable=False)
    radius_current = db.Column(db.Numeric(8, 3), nullable=False)
    resharpen_count = db.Column(db.Integer, nullable=False, default=0)
    scrapped_at = db.Column(db.DateTime)
    scrap_reason_id = db.Column(db.Integer, db.ForeignKey("scrap_reasons.id"))
    description = db.Column(db.Text)
    location_type = db.Column(db.String(32), nullable=False)
    location_machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"))
    location_tool_post_id = db.Column(db.Integer, db.ForeignKey("tool_posts.id"))
    location_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    installations = db.relationship("Installation", back_populates="cutter")
    resharpenings = db.relationship("Resharpening", back_populates="cutter")
    scrap_reason = db.relationship("ScrapReason")


class Machine(db.Model):
    __tablename__ = "machines"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    code = db.Column(db.String(64), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tool_posts = db.relationship("ToolPost", back_populates="machine")


class ToolPost(db.Model):
    __tablename__ = "tool_posts"

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    position = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    machine = db.relationship("Machine", back_populates="tool_posts")
    installations = db.relationship("Installation", back_populates="tool_post")


class Installation(db.Model):
    __tablename__ = "installations"

    id = db.Column(db.Integer, primary_key=True)
    cutter_id = db.Column(db.Integer, db.ForeignKey("cutters.id"), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)
    tool_post_id = db.Column(db.Integer, db.ForeignKey("tool_posts.id"), nullable=False)
    installed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    removed_at = db.Column(db.DateTime)
    removal_reason_id = db.Column(db.Integer, db.ForeignKey("removal_reasons.id"))
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    cutter = db.relationship("Cutter", back_populates="installations")
    tool_post = db.relationship("ToolPost", back_populates="installations")
    machine = db.relationship("Machine")
    removal_reason = db.relationship("RemovalReason")


class Resharpening(db.Model):
    __tablename__ = "resharpenings"

    id = db.Column(db.Integer, primary_key=True)
    cutter_id = db.Column(db.Integer, db.ForeignKey("cutters.id"), nullable=False)
    sharpened_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    radius_before = db.Column(db.Numeric(8, 3), nullable=False)
    radius_after = db.Column(db.Numeric(8, 3), nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    cutter = db.relationship("Cutter", back_populates="resharpenings")


class ScrapReason(db.Model):
    __tablename__ = "scrap_reasons"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)


class RemovalReason(db.Model):
    __tablename__ = "removal_reasons"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
