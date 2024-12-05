import os
import json
import math
from PIL import Image, ImageDraw


def round_corners(image, radius):
    """Rounds the corners of the image."""
    if radius <= 0:
        return image
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, *image.size), radius=radius, fill=255)
    image.putalpha(mask)
    return image


def resize_images(images, target_size):
    """Resizes all images to the target size."""
    return [
        (
            img.resize(target_size, Image.Resampling.LANCZOS)
            if img.size != target_size
            else img
        )
        for img in images
    ]


def load_layout(layout_file):
    """Loads the layout JSON file."""
    try:
        with open(layout_file, "r") as f:
            return json.load(f)
    except Exception as ex:
        raise RuntimeError(f"Error loading layout file: {ex}")


def calculate_layout(rule, img_objects, margin_spacing):
    """Calculates layout based on rule and image objects."""
    layout = []
    rows, cols = 0, 0
    collage_w, collage_h = 0, 0

    if isinstance(rule, dict):  # Layout specified as a dictionary
        rows, cols = rule["layout"]["rows"], rule["layout"]["columns"]
        configs = rule["layout"]["images"]
        row_heights = [0] * rows
        col_widths = [0] * cols

        # Calculate column widths and row heights
        for config in configs:
            row, col, span = config["row"] - 1, config["col"] - 1, config.get("span", 1)
            img = img_objects[configs.index(config)]
            w, h = img.size

            scaled_w = (w + (span - 1) * margin_spacing) / span
            col_widths[col : col + span] = [
                max(col_widths[c], scaled_w) for c in range(col, col + span)
            ]
            row_heights[row] = max(row_heights[row], h)

        # Adjust image sizes based on calculated widths and heights
        for config in configs:
            row, col, span = config["row"] - 1, config["col"] - 1, config.get("span", 1)
            img = img_objects[configs.index(config)]
            w, h = img.size

            total = (
                sum(col_widths[col : col + span]) + (span - 1) * margin_spacing
            )  # Total column width
            scale = total / w
            new_w = int(w * scale)
            new_h = int(h * scale)

            img_objects[configs.index(config)] = img.resize(
                (new_w, new_h), Image.Resampling.LANCZOS
            )
            row_heights[row] = max(row_heights[row], new_h)

        collage_w = int(sum(col_widths) + (cols + 1) * margin_spacing)
        collage_h = int(sum(row_heights) + (rows + 1) * margin_spacing)

        # Generate layout positions
        y = margin_spacing
        for row_i, row_h in enumerate(row_heights):
            x = margin_spacing
            for col_i, col_w in enumerate(col_widths):
                for config in configs:
                    if config["row"] - 1 == row_i and config["col"] - 1 == col_i:
                        layout.append({"x": x, "y": y})
                        break
                x += int(col_w + margin_spacing)
            y += int(row_h + margin_spacing)

    elif isinstance(rule, int):  # Grid layout specified by number of columns
        img_sizes = [img.size for img in img_objects]
        avg_width = sum(w for w, _ in img_sizes) // len(img_sizes)
        avg_height = sum(h for _, h in img_sizes) // len(img_sizes)

        rows = math.ceil(len(img_objects) / rule) if rule else 1
        cols = rule if rule else len(img_objects)

        collage_w = (
            (cols * avg_width) + (cols - 1) * margin_spacing + 2 * margin_spacing
        )
        collage_h = (
            (rows * avg_height) + (rows - 1) * margin_spacing + 2 * margin_spacing
        )

        layout = [
            {
                "x": margin_spacing + col * (avg_width + margin_spacing),
                "y": margin_spacing + row * (avg_height + margin_spacing),
            }
            for row in range(rows)
            for col in range(cols)
        ]

    else:
        raise ValueError("Invalid layout type specified.")

    return layout, collage_w, collage_h


def create_collage(
    input_dir, output_file, margin_spacing=0, corner_radius=0, rule=None
):
    """Creates a collage from images in the input directory."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Load images
    images = [
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.endswith((".png", ".jpg", ".jpeg"))
    ]
    if not images:
        raise ValueError("No images found in the input directory.")
    img_objects = [Image.open(img) for img in images]

    # Calculate layout and collage size
    layout, collage_w, collage_h = calculate_layout(rule, img_objects, margin_spacing)

    # Create a new blank image for the collage
    collage = Image.new("RGBA", (collage_w, collage_h), (255, 255, 255, 0))

    # Place images on the collage
    for index, img in enumerate(img_objects):
        x, y = layout[index]["x"], layout[index]["y"]
        if corner_radius > 0:
            img = round_corners(img, corner_radius)
        collage.paste(img, (x, y), img if img.mode == "RGBA" else None)

    collage.save(output_file)
    print(f"Collage saved as {output_file}")


if __name__ == "__main__":
    try:
        input_dir = input("Enter the input directory path: ").strip()
        output_file = input(
            "Enter the output file name (e.g., output/collage.png): "
        ).strip()
        use_layout = input("Use available layout? [y/n] (n): ").strip().lower() == "y"

        if use_layout:
            profile = input(
                "Enter the layout JSON file path (e.g., layout/layout.json): "
            ).strip()
            rule = load_layout(profile)
        else:
            columns = input(
                "Enter the number of columns (leave blank for default): "
            ).strip()
            rule = int(columns) if columns else 0

        margin_spacing = input("Enter margin/spacing (default: 0): ").strip()
        corner_radius = input("Enter corner radius (default: 0): ").strip()

        margin_spacing = int(margin_spacing) if margin_spacing else 0
        corner_radius = int(corner_radius) if corner_radius else 0

        create_collage(input_dir, output_file, margin_spacing, corner_radius, rule)

    except Exception as ex:
        print(f"An unexpected error occurred: {ex}")
        input("Press Enter to exit...")
