from PIL import Image, ImageDraw, ImageFont, ImageOps

# Function to create an image with a rounded rectangle, text, and an overlayed PNG image at the top
def create_text_image_with_overlay(text, font_size, overlay_image_path, output_path):
    # Set the fixed width (slightly less than a TikTok video width of 1080px)
    fixed_width = 500

    # Load the overlay image
    overlay_img = Image.open(overlay_image_path)
    overlay_img = overlay_img.resize((fixed_width, overlay_img.height * fixed_width // overlay_img.width), Image.Resampling.LANCZOS)
    overlay_height = overlay_img.height

    # Load a font with the given font size
    try:
        font = ImageFont.truetype("Montserrat-ExtraBold", font_size)
    except IOError:
        font = ImageFont.load_default()
        print("Default font is being used, and it may not respect the font size.")

    # Calculate the wrapped text and its height
    temp_img = Image.new('RGB', (fixed_width, 1))
    draw = ImageDraw.Draw(temp_img)
    lines = []
    words = text.split()
    line = ""

    for word in words:
        # Check if the current line with the next word would exceed the fixed width
        if draw.textlength(line + word, font=font) <= fixed_width - 4:  # 4 pixels for left and right padding
            line += word + " "
        else:
            lines.append(line.strip())
            line = word + " "
    lines.append(line.strip())

    # Calculate text height
    text_height = sum([draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines])

    # Define the specific padding values
    left_right_padding = 8
    top_padding = 10
    bottom_padding = 20

    # Adjust height to include overlay image and text
    height = text_height + top_padding + bottom_padding + overlay_height

    # Create a new image with calculated height and fixed width
    img = Image.new('RGBA', (fixed_width, height), color=(245, 245, 245, 255))

    # Create a rounded rectangle
    radius = 15
    rounded_rect = Image.new('L', (fixed_width, height), 0)
    draw_rounded = ImageDraw.Draw(rounded_rect)
    draw_rounded.rounded_rectangle([(0, 0), (fixed_width, height)], radius, fill=255)
    img.putalpha(rounded_rect)

    # Paste the overlay image at the top of the rectangle
    img.paste(overlay_img, (0, 0), overlay_img)

    # Draw the text onto the image below the overlay
    draw = ImageDraw.Draw(img)
    text_position_y = overlay_height + top_padding
    for line in lines:
        draw.text((left_right_padding, text_position_y), line, font=font, fill=(0, 0, 0, 255))
        line_height = draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
        text_position_y += line_height

    # Save the image
    img.save(output_path)
    return (output_path, height)
