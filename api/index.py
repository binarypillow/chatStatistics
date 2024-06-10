from flask import Flask, request, render_template
import json
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

APP_NAME = "chatStatistics"

LABELS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def allowed_file(filename):
    return filename.lower().endswith(".json")


@app.route("/")
def index():
    return render_template("index.html", app_title=APP_NAME)


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files or not allowed_file(request.files["file"].filename):
        return "Invalid file type. Only JSON files are allowed.", 400
    file = request.files["file"]
    data = json.load(file)
    name = data["name"]
    stats = calculate_statistics(data)
    return render_template("stats.html", name=name, stats=stats, app_title=APP_NAME)


def parse_dates(data):
    return {
        msg["date"]: datetime.strptime(msg["date"], "%Y-%m-%dT%H:%M:%S") for msg in data
    }


def get_user_messages_per_year(data, parsed_dates):
    user_messages_per_year = defaultdict(lambda: defaultdict(int))
    for msg in data:
        date = parsed_dates[msg["date"]]
        user_messages_per_year[date.year][(msg["from_id"], msg["from"])] += 1
    return user_messages_per_year


def get_top_users_per_year(user_messages_per_year):
    return {
        year: dict(sorted(users.items(), key=lambda item: item[1], reverse=True)[:3])
        for year, users in user_messages_per_year.items()
    }


def get_time_distribution(data, parsed_dates, first_message_date):
    time_distribution = defaultdict(int)
    for msg in data:
        date = parsed_dates[msg["date"]]
        time_distribution[(date.year, date.month)] += 1
    return [
        {
            "label": year,
            "data": [time_distribution.get((year, month), 0) for month in range(1, 13)],
        }
        for year in range(first_message_date.year, datetime.now().year + 1)
    ]


def create_figure(time_distribution):
    fig = go.Figure()
    for time_dict in time_distribution:
        fig.add_trace(
            go.Bar(
                x=LABELS,
                y=time_dict["data"],
                name=str(time_dict["label"]),
                text=time_dict["data"],
                textposition="auto",
                hoverinfo="none",
            )
        )
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Number of messages")
    fig.update_layout(
        template="plotly_white",
        legend=dict(yanchor="top", xanchor="right"),
        plot_bgcolor="rgba(248,249,250,255)",
        paper_bgcolor="rgba(248,249,250,255)",
    )
    fig.update_traces(
        textfont_size=12, textangle=0, textposition="outside", cliponaxis=False
    )
    return pio.to_html(
        fig,
        full_html=False,
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": [
                "zoom2d",
                "pan2d",
                "select2d",
                "lasso2d",
            ],
        },
    )


def calculate_statistics(data):
    joins_by_link = [
        msg
        for msg in data["messages"]
        if msg["type"] == "service" and msg["action"] == "join_group_by_link"
    ]

    invitations = [
        msg
        for msg in data["messages"]
        if msg["type"] == "service" and msg["action"] == "invite_members"
    ]
    messages = [msg for msg in data["messages"] if msg["type"] == "message"]
    parsed_dates = parse_dates(messages)
    timestamps = list(parsed_dates.values())
    first_message_date = min(timestamps)

    user_messages_per_year = get_user_messages_per_year(messages, parsed_dates)
    top_users_per_year = get_top_users_per_year(user_messages_per_year)

    time_distribution = get_time_distribution(
        messages, parsed_dates, first_message_date
    )

    fig_html = create_figure(time_distribution)

    return {
        "first_message_date": first_message_date,
        "total_messages": len(messages),
        "total_joins": len(joins_by_link),
        "total_invites": len(invitations),
        "top_users_per_year": top_users_per_year,
        "fig_html": fig_html,
    }


if __name__ == "__main__":
    app.run(debug=True)
