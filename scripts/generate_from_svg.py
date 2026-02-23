#!/usr/bin/env python3
"""从SVG矢量图生成高质量的PNG和ICO图标"""
from pathlib import Path
from PIL import Image

def generate_icons_from_svg():
    """从SVG生成PNG和ICO图标"""
    svg_path = Path("assets/koto_icon.svg")
    png_path = Path("assets/koto_icon.png")
    ico_path = Path("assets/koto_icon.ico")
    
    if not svg_path.exists():
        print(f"❌ 找不到SVG文件: {svg_path}")
        return False
    
    print(f"📄 找到SVG文件: {svg_path}")
    print("🎨 正在生成高质量图标...\n")
    
    try:
        # 尝试使用cairosvg
        try:
            from cairosvg import svg2png
            import io
            
            print("  使用 cairosvg 渲染SVG...")
            # 生成512x512的高质量PNG
            png_data = svg2png(
                url=str(svg_path),
                output_width=512,
                output_height=512
            )
            
            img = Image.open(io.BytesIO(png_data))
            print("  ✅ SVG转PNG成功（512x512）")
            
        except ImportError:
            print("  ⚠️  cairosvg未安装，尝试使用其他方法...")
            # 尝试使用svglib和reportlab
            try:
                from svglib.svglib import svg2rlg
                from reportlab.graphics import renderPM
                import io
                
                print("  使用 svglib 渲染SVG...")
                drawing = svg2rlg(str(svg_path))
                png_data = renderPM.drawToString(drawing, fmt='PNG')
                img = Image.open(io.BytesIO(png_data))
                img = img.resize((512, 512), Image.Resampling.LANCZOS)
                print("  ✅ SVG转PNG成功（512x512）")
                
            except ImportError:
                print("  ⚠️  svglib未安装，使用PIL直接处理...")
                # 如果都没有，尝试用PIL打开（某些SVG可能支持）
                try:
                    img = Image.open(str(svg_path))
                    img = img.resize((512, 512), Image.Resampling.LANCZOS)
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                except Exception:
                    print("❌ 无法转换SVG，请安装 cairosvg 或 svglib")
                    print("\n安装命令:")
                    print("  pip install cairosvg")
                    print("  或")
                    print("  pip install svglib reportlab")
                    return False
        
        # 备份现有图标
        if png_path.exists():
            backup = png_path.with_suffix('.png.backup')
            png_path.rename(backup)
            print(f"  ✅ 备份原PNG: {backup.name}")
        
        if ico_path.exists():
            backup = ico_path.with_suffix('.ico.backup')
            ico_path.rename(backup)
            print(f"  ✅ 备份原ICO: {backup.name}")
        
        # 保存PNG（512x512高质量）
        img = img.resize((512, 512), Image.Resampling.LANCZOS)
        img.save(str(png_path), 'PNG', optimize=True)
        print(f"  ✅ 保存PNG: {png_path}")
        
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
        print(f"  ✅ 保存ICO: {ico_path}")
        
        print("\n🎉 图标生成完成！")
        print("💡 请重启 Koto 应用以应用新图标")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = generate_icons_from_svg()
    sys.exit(0 if success else 1)
