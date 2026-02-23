#!/usr/bin/env python3
"""重新绘制Koto图标（基于SVG设计）"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_koto_icon(size=512):
    """创建Koto图标（高质量版本）"""
    print(f"🎨 绘制 {size}x{size} 图标...")
    
    # 创建画布（RGBA支持透明）
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 计算缩放比例（SVG是256x256）
    scale = size / 256
    
    # 背景渐变（用纯色代替，PIL不支持原生渐变）
    # 颜色从 #4F8CFF 到 #2F6BFF，使用中间色
    bg_color = (63, 123, 255, 255)  # 混合色
    corner_radius = int(56 * scale)
    
    # 绘制圆角矩形背景
    draw.rounded_rectangle(
        [0, 0, size, size],
        radius=corner_radius,
        fill=bg_color
    )
    
    # 绘制白色圆形
    center = size // 2
    circle_radius = int(80 * scale)
    draw.ellipse(
        [
            center - circle_radius,
            center - circle_radius,
            center + circle_radius,
            center + circle_radius
        ],
        fill=(255, 255, 255, 255)
    )
    
    # 绘制蓝色横条（三条）
    bar_color = (47, 107, 255, 255)
    bar_width = int(112 * scale)
    bar_height = int(16 * scale)
    bar_radius = int(8 * scale)
    bar_x = int(72 * scale)
    
    # 第一条
    draw.rounded_rectangle(
        [bar_x, int(88 * scale), bar_x + bar_width, int(104 * scale)],
        radius=bar_radius,
        fill=bar_color
    )
    
    # 第二条
    draw.rounded_rectangle(
        [bar_x, int(120 * scale), bar_x + bar_width, int(136 * scale)],
        radius=bar_radius,
        fill=bar_color
    )
    
    # 第三条
    draw.rounded_rectangle(
        [bar_x, int(152 * scale), bar_x + bar_width, int(168 * scale)],
        radius=bar_radius,
        fill=bar_color
    )
    
    # 尝试添加文字"Koto"
    try:
        font_size = int(20 * scale)
        # 尝试使用系统字体
        try:
            font = ImageFont.truetype("seguiui.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("msyh.ttc", font_size)  # 微软雅黑
            except:
                font = ImageFont.load_default()
        
        text = "Koto"
        text_color = (232, 239, 255, 255)
        
        # 获取文字边界框
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (size - text_width) // 2
        text_y = int(214 * scale) - text_height
        
        draw.text((text_x, text_y), text, fill=text_color, font=font)
        print("  ✅ 已添加文字")
    except Exception as e:
        print(f"  ⚠️  文字添加失败（可忽略）: {e}")
    
    return img

def main():
    """生成图标"""
    png_path = Path("assets/koto_icon.png")
    ico_path = Path("assets/koto_icon.ico")
    
    print("🎨 重新绘制Koto图标（基于SVG设计）\n")
    
    # 备份现有图标
    if png_path.exists():
        backup = png_path.with_suffix('.png.backup')
        png_path.rename(backup)
        print(f"✅ 备份原PNG: {backup.name}")
    
    if ico_path.exists():
        backup = ico_path.with_suffix('.ico.backup')
        ico_path.rename(backup)
        print(f"✅ 备份原ICO: {backup.name}\n")
    
    # 生成512x512高质量图标
    img = create_koto_icon(512)
    
    # 保存PNG
    img.save(str(png_path), 'PNG', optimize=True)
    print(f"✅ 保存PNG: {png_path} (512x512)")
    
    # 生成多尺寸ICO
    img.save(
        str(ico_path),
        format='ICO',
        sizes=[
            (256, 256),
            (128, 128),
            (64, 64),
            (48, 48),
            (32, 32),
            (16, 16)
        ]
    )
    print(f"✅ 保存ICO: {ico_path} (多尺寸)")
    
    print("\n🎉 图标生成完成！")
    print("💡 请重启 Koto 应用以应用新图标")
    
    return True

if __name__ == "__main__":
    import sys
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
