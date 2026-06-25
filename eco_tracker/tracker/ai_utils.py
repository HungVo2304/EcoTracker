import random


ALLOWED_AI_CATEGORIES = [
    "recycling",
    "tree_planting",
    "green_transport",
    "clean_up",
    "saving_energy",
    "reusable_item",
]


def classify_eco_image(image_file):
    file_name = image_file.name.lower()

    if "tree" in file_name or "plant" in file_name or "garden" in file_name:
        category = "tree_planting"
        reason = "The file name suggests a tree planting or gardening activity."
    elif "bike" in file_name or "cycle" in file_name or "walk" in file_name:
        category = "green_transport"
        reason = "The file name suggests green transportation."
    elif "trash" in file_name or "clean" in file_name or "litter" in file_name:
        category = "clean_up"
        reason = "The file name suggests a clean-up activity."
    elif "light" in file_name or "energy" in file_name or "electric" in file_name:
        category = "saving_energy"
        reason = "The file name suggests saving energy."
    elif "bag" in file_name or "bottle" in file_name or "cup" in file_name:
        category = "reusable_item"
        reason = "The file name suggests using a reusable item."
    elif "recycle" in file_name or "plastic" in file_name or "paper" in file_name:
        category = "recycling"
        reason = "The file name suggests recycling."
    else:
        category = random.choice(ALLOWED_AI_CATEGORIES)
        reason = "Demo AI mode: category selected for testing without API credits."

    return {
        "category": category,
        "confidence": 0.82,
        "reason": reason,
        "is_eco_action": True,
    }