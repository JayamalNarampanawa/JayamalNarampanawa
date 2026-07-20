import os
import requests
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape

GITLAB_USERNAME = "JayamalNarampanawa"
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
OUTPUT_FILE = "assets/gitlab-contribution-graph.svg"

if not GITLAB_TOKEN:
    raise RuntimeError("GITLAB_TOKEN environment variable is missing.")

headers = {
    "PRIVATE-TOKEN": GITLAB_TOKEN
}

# Get GitLab user ID
user_response = requests.get(
    "https://gitlab.com/api/v4/users",
    params={"username": GITLAB_USERNAME},
    headers=headers,
    timeout=30,
)
user_response.raise_for_status()

users = user_response.json()
if not users:
    raise RuntimeError(f"GitLab user '{GITLAB_USERNAME}' was not found.")

user_id = users[0]["id"]

# Collect recent activity events.
# GitLab's Events API is paginated and does not expose an exact clone
# of the contribution calendar, so this visualizes API-visible activity.
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

# Count events per UTC date
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

# GitHub-style 52-week calendar ending this week
start_date = today - timedelta(days=364)

# Align to Sunday
start_date -= timedelta(days=(start_date.weekday() + 1) % 7)

weeks = 53
cell = 11
gap = 3
left_padding = 45
top_padding = 55

width = left_padding + weeks * (cell + gap) + 25
height = top_padding + 7 * (cell + gap) + 50

def activity_color(count: int) -> str:
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
        current_date = start_date + timedelta(days=(week * 7 + day))

        if current_date > today:
            count = 0
        else:
            count = activity.get(current_date, 0)

        x = left_padding + week * (cell + gap)
        y = top_padding + day * (cell + gap)

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
                <title>{escape(str(current_date))}: {count} GitLab activities</title>
            </rect>
            '''
        )

total_events = sum(
    count
    for date, count in activity.items()
    if date >= start_date
)

svg = f'''<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}"
>
    <rect width="100%" height="100%" rx="12" fill="#0D1117"/>

    <text
        x="20"
        y="28"
        fill="#E6EDF3"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="16"
        font-weight="600"
    >
        GitLab Activity
    </text>

    <text
        x="20"
        y="46"
        fill="#8B949E"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="11"
    >
        {total_events} API-visible activities in the displayed period
    </text>

    <text x="15" y="{top_padding + 10}" fill="#8B949E" font-size="9">Sun</text>
    <text x="15" y="{top_padding + 2 * (cell + gap) + 10}" fill="#8B949E" font-size="9">Tue</text>
    <text x="15" y="{top_padding + 4 * (cell + gap) + 10}" fill="#8B949E" font-size="9">Thu</text>
    <text x="15" y="{top_padding + 6 * (cell + gap) + 10}" fill="#8B949E" font-size="9">Sat</text>

    {''.join(rects)}

    <text
        x="20"
        y="{height - 18}"
        fill="#8B949E"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="10"
    >
        Source: GitLab Events API · @{GITLAB_USERNAME}
    </text>
</svg>
'''

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    file.write(svg)

print(f"Generated {OUTPUT_FILE}")