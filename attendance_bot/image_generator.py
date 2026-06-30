import os
import io
import subprocess
from PIL import Image, ImageDraw, ImageFont

def get_japanese_font():
    """Dynamically find a Japanese font available on the system."""
    fallbacks = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    ]
    
    try:
        result = subprocess.run(['fc-match', '-f', '%{file}', ':lang=ja'], capture_output=True, text=True)
        if result.stdout and os.path.exists(result.stdout.strip()):
            return result.stdout.strip()
    except Exception:
        pass
    
    for path in fallbacks:
        if os.path.exists(path):
            return path
            
    return None

def create_summary_image(categories, is_saturday, today_str, is_test, display_order):
    # Image configuration - Vertical mobile-friendly layout
    width = 720
    header_height = 140
    line_height = 56
    category_padding = 40
    
    # Calculate required height
    total_users_lines = sum(len(users) if users else 1 for users in categories.values())
    height = header_height + 60 + (len(categories) * (category_padding + 60)) + (total_users_lines * line_height)
    height = int(max(height, 800)) # Minimum height

    # Create image canvas
    bg_color = (244, 244, 249) # Light modern gray background
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    font_path = get_japanese_font()
    try:
        title_font = ImageFont.truetype(font_path, 42) if font_path else ImageFont.load_default()
        category_font = ImageFont.truetype(font_path, 32) if font_path else ImageFont.load_default()
        text_font = ImageFont.truetype(font_path, 28) if font_path else ImageFont.load_default()
        small_font = ImageFont.truetype(font_path, 22) if font_path else ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        category_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Draw Header (Modern Indigo)
    header_color = (79, 70, 229) 
    draw.rectangle([0, 0, width, header_height], fill=header_color)
    
    prefix = "【テスト】" if is_test else ""
    title_text = f"{prefix}出欠集計結果"
    
    draw.text((40, 30), title_text, fill=(255, 255, 255), font=title_font)
    if is_saturday:
        total_joined = len(categories.get("出席", []))
    else:
        total_joined = sum(len(categories.get(c, [])) for c in ["3限終わり", "4限終わり", "5限終わり"])
    draw.text((40, 90), f"日付: {today_str}   |   合計参加: {total_joined}人", fill=(224, 231, 255), font=small_font)

    # Colors for categories
    cat_colors = {
        "3限終わり": (16, 185, 129), # Emerald green
        "4限終わり": (59, 130, 246), # Blue
        "5限終わり": (245, 158, 11), # Amber
        "出席": (16, 185, 129),       # Emerald green
        "欠席": (239, 68, 68),        # Red
        "未回答者": (156, 163, 175)    # Gray
    }

    current_y = header_height + 40

    for col in display_order:
        users = categories[col]
        color = cat_colors.get(col, (100, 100, 100))
        
        card_margin_x = 40
        
        # Category Accent Line
        try:
            draw.rounded_rectangle([card_margin_x, current_y, card_margin_x + 8, current_y + 40], radius=4, fill=color)
        except AttributeError:
            draw.rectangle([card_margin_x, current_y, card_margin_x + 8, current_y + 40], fill=color)
        
        # Category Title
        draw.text((card_margin_x + 28, current_y + 2), f"{col} ({len(users)}人)", fill=(31, 41, 55), font=category_font)
        
        current_y += 60
        
        # Draw users
        if not users:
            draw.text((card_margin_x + 28, current_y + 8), "なし", fill=(156, 163, 175), font=text_font)
            current_y += line_height
        else:
            for name in users:
                # User Card Background
                try:
                    draw.rounded_rectangle([card_margin_x + 20, current_y, width - card_margin_x, current_y + 48], radius=8, fill=(255, 255, 255))
                except AttributeError:
                    draw.rectangle([card_margin_x + 20, current_y, width - card_margin_x, current_y + 48], fill=(255, 255, 255))
                
                # User Name Text
                draw.text((card_margin_x + 40, current_y + 8), name, fill=(75, 85, 99), font=text_font)
                current_y += line_height
                
        current_y += category_padding

    # Save to binary stream
    image_binary = io.BytesIO()
    img.save(image_binary, 'PNG')
    image_binary.seek(0)
    return image_binary
