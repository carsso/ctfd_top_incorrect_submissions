from flask import Blueprint, render_template, request, url_for
from wtforms import SelectField, StringField
from wtforms.validators import InputRequired

from CTFd.forms import BaseForm
from CTFd.forms.fields import SubmitField
from CTFd.models import Challenges, Submissions, db
from CTFd.utils.decorators import admins_only
from CTFd.utils.helpers.models import build_model_filters

plugin_top_incorrect_submissions = Blueprint(
    "top_incorrect_submissions", __name__, template_folder="templates"
)


@plugin_top_incorrect_submissions.route("/admin/top_incorrect_submissions")
@admins_only
def top_incorrect_submissions_chall():
    submission_type = "incorrect"
    filters_by = {"type": submission_type}
    filters = []

    q = request.args.get("q")
    field = request.args.get("field")
    page = abs(request.args.get("page", 1, type=int))

    filters = build_model_filters(
        model=Submissions,
        query=q,
        field=field,
        extra_columns={"challenge_name": Challenges.name,},
    )

    submissions = (
        Submissions.query.with_entities(
            db.func.count(db.func.distinct(Submissions.user_id)).label(
                "sum_single_user"
            ),
            db.func.count(Submissions.user_id).label("sum"),
            db.func.max(Submissions.date).label("date"),
            Submissions.challenge_id,
            Submissions.provided,
            Challenges.name.label("challenge_name"),
        )
        .filter_by(**filters_by)
        .join(Challenges)
        .filter(*filters)
        .order_by(
            db.func.count(db.func.distinct(Submissions.user_id)).desc(),
            db.func.count(Submissions.user_id).desc(),
        )
        .group_by(Submissions.challenge_id, Submissions.provided)
        .paginate(page=page, per_page=50)
    )

    args = dict(request.args)
    args.pop("page", 1)

    return render_template(
        "top_incorrect_submissions.html",
        submissions=submissions,
        prev_page=url_for(request.endpoint, page=submissions.prev_num, **args),
        next_page=url_for(request.endpoint, page=submissions.next_num, **args),
        q=q,
        field=field,
        TopSubmissionSearchForm=TopSubmissionSearchForm,
    )


class TopSubmissionSearchForm(BaseForm):
    field = SelectField(
        "Search Field",
        choices=[
            ("provided", "Provided"),
            ("challenge_id", "Challenge ID"),
            ("challenge_name", "Challenge Name"),
        ],
        default="provided",
        validators=[InputRequired()],
    )
    q = StringField("Parameter", validators=[InputRequired()])
    submit = SubmitField("Search")


def load(app):
    app.db.create_all()
    app.register_blueprint(plugin_top_incorrect_submissions)
