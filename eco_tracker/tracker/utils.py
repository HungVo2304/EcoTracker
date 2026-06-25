ECO_LEVELS = [
    {
        "name": "Eco Beginner",
        "icon": "🌱",
        "min_points": 0,
        "max_points": 100,
        "description": "You are starting your eco journey.",
    },
    {
        "name": "Green Starter",
        "icon": "🍃",
        "min_points": 100,
        "max_points": 300,
        "description": "You are building consistent green habits.",
    },
    {
        "name": "Eco Warrior",
        "icon": "🌿",
        "min_points": 300,
        "max_points": 600,
        "description": "Your actions are creating visible positive impact.",
    },
    {
        "name": "Planet Protector",
        "icon": "🌍",
        "min_points": 600,
        "max_points": 1000,
        "description": "You are strongly contributing to the planet.",
    },
    {
        "name": "Climate Champion",
        "icon": "🏆",
        "min_points": 1000,
        "max_points": 1500,
        "description": "You are leading by example.",
    },
    {
        "name": "Earth Guardian",
        "icon": "🛡️",
        "min_points": 1500,
        "max_points": None,
        "description": "You have reached the highest eco level.",
    },
]


def get_level_info(total_points):
    total_points = total_points or 0

    for level in ECO_LEVELS:
        min_points = level["min_points"]
        max_points = level["max_points"]

        if max_points is None or min_points <= total_points < max_points:
            if max_points is None:
                progress_percent = 100
                points_to_next = 0
                next_level = None
            else:
                points_in_level = total_points - min_points
                points_needed_for_level = max_points - min_points
                progress_percent = int((points_in_level / points_needed_for_level) * 100)
                points_to_next = max_points - total_points

                next_level = None
                current_index = ECO_LEVELS.index(level)
                if current_index + 1 < len(ECO_LEVELS):
                    next_level = ECO_LEVELS[current_index + 1]["name"]

            return {
                "name": level["name"],
                "icon": level["icon"],
                "description": level["description"],
                "min_points": min_points,
                "max_points": max_points,
                "progress_percent": progress_percent,
                "points_to_next": points_to_next,
                "next_level": next_level,
            }

    return ECO_LEVELS[0]