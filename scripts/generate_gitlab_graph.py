import os
import requests
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape

GITLAB_USERNAME = "JayamalNarampanawa"
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")

CONTRIBUTION_OUTPUT = "assets/gitlab-contribution-graph.svg"
ACTIVITY_OUTPUT = "assets/gitlab-activity-graph.svg"

if not GITLAB_TOKEN:
    raise RuntimeError("GITLAB_TOKEN environment variable is missing.")

headers = {
    "PRIVATE-TOKEN": GITLAB_TOKEN
}

# --------------------------------------------------
# GET GITLAB USER
# --------------------------------------------------

user_response = requests.get(
    "https://gitlab.com/api/v4/users",
    params={"username": GITLAB_USERNAME},
    headers=headers,
    timeout=30,
)

user_response.raise_for_status()

users = user_response.json()

if not users:
    raise RuntimeError(
        f"GitLab user '{GITLAB_USERNAME}' was not found."
    )

user_id = users[0]["id"]


# --------------------------------------------------
# FETCH GITLAB EVENTS
# --------------------------------------------------

events = []

page = 1

while page <= 10:

    response = requests.get(
        f"https://gitlab.com/api/v4/users/{user_id}/events",
        headers=headers,
        params={
            "per_page": 100,
            "page": page,
        },
        timeout=30,
    )

    response.raise_for_status()

    batch = response.json()

    if not batch:
        break

    events.extend(batch)

    if len(batch) < 100:
        break

    page += 1


# --------------------------------------------------
# COUNT ACTIVITY BY DATE
# --------------------------------------------------

activity = Counter()

for event in events:

    created_at = event.get("created_at")

    if not created_at:
        continue

    date = datetime.fromisoformat(
        created_at.replace("Z", "+00:00")
    ).date()

    activity[date] += 1


today = datetime.now(timezone.utc).date()


# ==================================================
# GITLAB CONTRIBUTION GRID
# ==================================================

start_date = today - timedelta(days=364)

# Align calendar to Sunday
start_date -= timedelta(
    days=(start_date.weekday() + 1) % 7
)

weeks = 53

cell = 11
gap = 3

left_padding = 45
top_padding = 55

width = (
    left_padding
    + weeks * (cell + gap)
    + 25
)

height = (
    top_padding
    + 7 * (cell + gap)
    + 50
)


def activity_color(count):

    if count == 0:
        return "#161B22"

    if count == 1:
        return "#0D47A1"

    if count <= 3:
        return "#1565C0"

    if count <= 6:
        return "#1E88E5"

    return "#42A5F5"


rects = []

for week in range(weeks):

    for day in range(7):

        current_date = (
            start_date
            + timedelta(
                days=(week * 7 + day)
            )
        )

        if current_date > today:
            count = 0

        else:
            count = activity.get(
                current_date,
                0
            )

        x = (
            left_padding
            + week * (cell + gap)
        )

        y = (
            top_padding
            + day * (cell + gap)
        )

        color = activity_color(count)

        rects.append(
            f'''
            <rect
                x="{x}"
                y="{y}"
                width="{cell}"
                height="{cell}"
                rx="2"
                fill="{color}"
            >
                <title>
                {escape(str(current_date))}:
                {count} GitLab activities
                </title>
            </rect>
            '''
        )


total_events = sum(
    count
    for date, count in activity.items()
    if date >= start_date
)


contribution_svg = f'''
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}"
>

<rect
    width="100%"
    height="100%"
    rx="12"
    fill="#0D1117"
/>

<text
    x="20"
    y="28"
    fill="#E6EDF3"
    font-family="Segoe UI, Arial"
    font-size="16"
    font-weight="600"
>
GitLab Activity
</text>

<text
    x="20"
    y="46"
    fill="#8B949E"
    font-family="Segoe UI, Arial"
    font-size="11"
>
{total_events} API-visible activities
</text>

{''.join(rects)}

<text
    x="20"
    y="{height - 18}"
    fill="#8B949E"
    font-family="Segoe UI, Arial"
    font-size="10"
>
Source: GitLab Events API · @{GITLAB_USERNAME}
</text>

</svg>
'''


# ==================================================
# GITLAB ACTIVITY LINE GRAPH
# ==================================================

graph_days = 90

graph_start = (
    today
    - timedelta(days=graph_days - 1)
)

daily_data = []

for index in range(graph_days):

    date = (
        graph_start
        + timedelta(days=index)
    )

    daily_data.append(
        (
            date,
            activity.get(date, 0)
        )
    )


graph_width = 900
graph_height = 320

padding_left = 55
padding_right = 25

padding_top = 55
padding_bottom = 55

chart_width = (
    graph_width
    - padding_left
    - padding_right
)

chart_height = (
    graph_height
    - padding_top
    - padding_bottom
)


max_activity = max(
    [
        count
        for _, count
        in daily_data
    ]
    or [1]
)

max_activity = max(
    max_activity,
    1
)


points = []

for index, (
    date,
    count
) in enumerate(daily_data):

    x = (
        padding_left
        + (
            index
            / (graph_days - 1)
        )
        * chart_width
    )

    y = (
        padding_top
        + chart_height
        - (
            count
            / max_activity
        )
        * chart_height
    )

    points.append(
        (
            x,
            y,
            date,
            count
        )
    )


polyline_points = " ".join(
    f"{x:.2f},{y:.2f}"
    for x, y, _, _
    in points
)


point_circles = []

for x, y, date, count in points:

    if count > 0:

        point_circles.append(
            f'''
            <circle
                cx="{x:.2f}"
                cy="{y:.2f}"
                r="3"
                fill="#FFFFFF"
            >
                <title>
                {date}: {count}
                GitLab activities
                </title>
            </circle>
            '''
        )


grid_lines = []

for i in range(5):

    y = (
        padding_top
        + (
            chart_height / 4
        ) * i
    )

    grid_lines.append(
        f'''
        <line
            x1="{padding_left}"
            y1="{y}"
            x2="{graph_width - padding_right}"
            y2="{y}"
            stroke="#21262D"
            stroke-width="1"
        />
        '''
    )


area_points = (
    f"{padding_left},"
    f"{padding_top + chart_height} "
    + polyline_points
    + " "
    + f"{graph_width - padding_right},"
    f"{padding_top + chart_height}"
)


activity_svg = f'''
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{graph_width}"
    height="{graph_height}"
    viewBox="0 0 {graph_width} {graph_height}"
>

<defs>

<linearGradient
    id="areaGradient"
    x1="0"
    y1="0"
    x2="0"
    y2="1"
>

<stop
    offset="0%"
    stop-color="#1E88E5"
    stop-opacity="0.45"
/>

<stop
    offset="100%"
    stop-color="#1E88E5"
    stop-opacity="0"
/>

</linearGradient>

</defs>


<rect
    width="100%"
    height="100%"
    rx="12"
    fill="#0D1117"
/>


<text
    x="25"
    y="30"
    fill="#E6EDF3"
    font-family="Segoe UI, Arial"
    font-size="18"
    font-weight="600"
>
GitLab Contribution Activity
</text>


<text
    x="25"
    y="48"
    fill="#8B949E"
    font-family="Segoe UI, Arial"
    font-size="11"
>
Activity trend over the last 90 days
</text>


{''.join(grid_lines)}


<polygon
    points="{area_points}"
    fill="url(#areaGradient)"
/>


<polyline
    points="{polyline_points}"
    fill="none"
    stroke="#1E88E5"
    stroke-width="3"
    stroke-linejoin="round"
    stroke-linecap="round"
/>


{''.join(point_circles)}


<text
    x="{padding_left}"
    y="{graph_height - 20}"
    fill="#8B949E"
    font-family="Segoe UI, Arial"
    font-size="10"
>
{graph_start}
</text>


<text
    x="{graph_width - 95}"
    y="{graph_height - 20}"
    fill="#8B949E"
    font-family="Segoe UI, Arial"
    font-size="10"
>
{today}
</text>


</svg>
'''


# --------------------------------------------------
# SAVE SVG FILES
# --------------------------------------------------

os.makedirs(
    "assets",
    exist_ok=True
)


with open(
    CONTRIBUTION_OUTPUT,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        contribution_svg
    )


with open(
    ACTIVITY_OUTPUT,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        activity_svg
    )


print(
    f"Generated "
    f"{CONTRIBUTION_OUTPUT}"
)

print(
    f"Generated "
    f"{ACTIVITY_OUTPUT}"
)