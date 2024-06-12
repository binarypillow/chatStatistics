from flask import Flask, request, render_template
import json
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

APP_NAME = "chatStatistics"

LABELS = {
    "month": [
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
    ],
    "day": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
}


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
    group_name = data["name"]

    first_timestamp = data["messages"][0]["date"]
    data_by_year = defaultdict(list)
    for msg in data["messages"]:
        year = datetime.strptime(msg["date"], "%Y-%m-%dT%H:%M:%S").year
        data_by_year[year].append(msg)

    stats = calculate_statistics(data_by_year, first_timestamp)

    return render_template(
        "stats.html", name=group_name, stats=stats, app_title=APP_NAME
    )


def get_user_messages(msgs):
    user_msgs = defaultdict(int)
    for m in msgs:
        user_name = m["from"]
        user_id = m["from_id"]
        user_msgs[(user_id, user_name)] += 1
    return user_msgs


def get_top_users(msgs):
    sorted_msgs = sorted(msgs.items(), key=lambda item: item[1], reverse=True)
    return dict(sorted_msgs[:3])


def get_time_dist(msgs, time_unit):
    if time_unit == "month":
        time_dist = {i: 0 for i in range(1, 13)}
    elif time_unit == "day":
        time_dist = {i: 0 for i in range(7)}
    else:
        raise ValueError("Invalid time_unit. Choose either 'month', 'day' or 'hour'.")

    for m in msgs:
        time = datetime.strptime(m["date"], "%Y-%m-%dT%H:%M:%S")
        if time_unit == "month":
            time = time.month
        elif time_unit == "day":
            time = time.weekday()
        time_dist[time] += 1

    return time_dist


def create_figure(time_dist, time_unit):
    fig = go.Figure()
    for y in time_dist:
        fig.add_trace(
            go.Bar(
                x=LABELS[time_unit],
                y=list(time_dist[y].values()),
                name=str(y),
                textposition="auto",
                hoverinfo="none",
            )
        )
    fig.update_xaxes(title_text=time_unit)
    fig.update_yaxes(title_text="number of messages")
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


def calculate_statistics(dt_by_year, first_t):
    num_messages = 0
    num_link_joins_by_year = defaultdict(int)
    num_invite_joins_by_year = defaultdict(int)
    msgs_by_year = defaultdict(dict)
    top_users_by_year = defaultdict(dict)

    monthly_time_dist_by_year = defaultdict(dict)
    daily_time_dist_by_year = defaultdict(dict)

    for y in dt_by_year:
        num_messages = num_messages + len(dt_by_year[y])

        num_link_joins_by_year[y] = len(
            [
                dt
                for dt in dt_by_year[y]
                if dt["type"] == "service" and dt["action"] == "join_group_by_link"
            ]
        )
        num_invite_joins_by_year[y] = len(
            [
                dt
                for dt in dt_by_year[y]
                if dt["type"] == "service" and dt["action"] == "invite_members"
            ]
        )
        msgs_by_year[y] = [dt for dt in dt_by_year[y] if dt["type"] == "message"]
        user_msgs_by_year = get_user_messages(msgs_by_year[y])
        top_users_by_year[y] = get_top_users(user_msgs_by_year)

        monthly_time_dist_by_year[y] = get_time_dist(msgs_by_year[y], "month")
        daily_time_dist_by_year[y] = get_time_dist(msgs_by_year[y], "day")

    monthly_fig = create_figure(monthly_time_dist_by_year, "month")
    daily_fig = create_figure(daily_time_dist_by_year, "day")

    return {
        "first_timestamp": first_t,
        "num_messages": num_messages,
        "num_joins": sum(num_link_joins_by_year.values()),
        "num_invites": sum(num_invite_joins_by_year.values()),
        "num_joins_by_year": num_link_joins_by_year,
        "num_invites_by_year": num_invite_joins_by_year,
        "top_users_by_year": top_users_by_year,
        "monthly_fig": monthly_fig,
        "daily_fig": daily_fig,
    }


if __name__ == "__main__":
    app.run(debug=True)
