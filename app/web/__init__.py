from flask import Blueprint, redirect, render_template, url_for

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    return redirect(url_for("web.dashboard"))


@web_bp.get("/login")
def login_page():
    return render_template("auth/login.html")


@web_bp.get("/ui/dashboard")
def dashboard():
    return render_template("dashboard/index.html")


@web_bp.get("/ui/me")
def me_page():
    return render_template("me/index.html")


@web_bp.get("/ui/peers")
def peers():
    return render_template("peers/index.html")


@web_bp.get("/ui/groups")
def groups():
    return render_template("groups/index.html")


@web_bp.get("/ui/hardware")
def hardware():
    return render_template("system/hardware.html")


@web_bp.get("/ui/interfaces")
def interfaces():
    return render_template("interfaces/index.html")
