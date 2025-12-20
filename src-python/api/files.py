"""
文件服务 API - 提供本地文件访问
用于在前端显示本地图片、视频缩略图等资源
"""

import io
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
import mimetypes

router = APIRouter(tags=["files"])


def _get_windows_thumbnail(file_path: str, size: int = 128) -> bytes | None:
    """
    使用 Windows Shell API 获取系统缩略图
    
    Args:
        file_path: 文件绝对路径
        size: 缩略图尺寸
        
    Returns:
        PNG 图片字节数据，失败返回 None
    """
    if sys.platform != 'win32':
        return None
    
    try:
        import ctypes
        from ctypes import wintypes
        from PIL import Image
        
        # COM 初始化
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)
        
        try:
            # 定义 GUID 结构
            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", wintypes.BYTE * 8)
                ]
            
            # IShellItemImageFactory GUID: {bcc18b79-ba16-442f-80c4-8a59c30c463b}
            IID_IShellItemImageFactory = GUID(
                0xbcc18b79, 0xba16, 0x442f,
                (wintypes.BYTE * 8)(0x80, 0xc4, 0x8a, 0x59, 0xc3, 0x0c, 0x46, 0x3b)
            )
            
            # SIZE 结构
            class SIZE(ctypes.Structure):
                _fields_ = [("cx", ctypes.c_int), ("cy", ctypes.c_int)]
            
            # 加载函数
            shell32 = ctypes.windll.shell32
            SHCreateItemFromParsingName = shell32.SHCreateItemFromParsingName
            SHCreateItemFromParsingName.argtypes = [
                wintypes.LPCWSTR, ctypes.c_void_p, 
                ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)
            ]
            SHCreateItemFromParsingName.restype = ctypes.HRESULT
            
            # 创建 IShellItem
            shell_item = ctypes.c_void_p()
            hr = SHCreateItemFromParsingName(
                file_path, None,
                ctypes.byref(IID_IShellItemImageFactory),
                ctypes.byref(shell_item)
            )
            
            if hr != 0 or not shell_item:
                return None
            
            # 获取 IShellItemImageFactory 的 GetImage 方法
            # VTable 偏移: QueryInterface=0, AddRef=1, Release=2, GetImage=3
            vtable = ctypes.cast(
                ctypes.cast(shell_item, ctypes.POINTER(ctypes.c_void_p)).contents,
                ctypes.POINTER(ctypes.c_void_p * 4)
            ).contents
            
            # GetImage 函数原型
            SIIGBF_RESIZETOFIT = 0x00000000
            GetImageProto = ctypes.WINFUNCTYPE(
                ctypes.HRESULT,
                ctypes.c_void_p,  # this
                SIZE,            # size
                ctypes.c_int,    # flags
                ctypes.POINTER(wintypes.HBITMAP)  # phbm
            )
            GetImage = GetImageProto(vtable[3])
            
            # 调用 GetImage
            hbitmap = wintypes.HBITMAP()
            hr = GetImage(shell_item, SIZE(size, size), SIIGBF_RESIZETOFIT, ctypes.byref(hbitmap))
            
            if hr != 0 or not hbitmap:
                # 释放 shell_item
                ReleaseProto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
                Release = ReleaseProto(vtable[2])
                Release(shell_item)
                return None
            
            # 将 HBITMAP 转换为 PIL Image
            gdi32 = ctypes.windll.gdi32
            user32 = ctypes.windll.user32
            
            # BITMAP 结构
            class BITMAP(ctypes.Structure):
                _fields_ = [
                    ("bmType", wintypes.LONG),
                    ("bmWidth", wintypes.LONG),
                    ("bmHeight", wintypes.LONG),
                    ("bmWidthBytes", wintypes.LONG),
                    ("bmPlanes", wintypes.WORD),
                    ("bmBitsPixel", wintypes.WORD),
                    ("bmBits", ctypes.c_void_p)
                ]
            
            # 获取位图信息
            bmp = BITMAP()
            gdi32.GetObjectW(hbitmap, ctypes.sizeof(BITMAP), ctypes.byref(bmp))
            
            width = bmp.bmWidth
            height = bmp.bmHeight
            
            # BITMAPINFOHEADER
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", wintypes.DWORD),
                    ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)
                ]
            
            # 创建 DC 并获取像素数据
            hdc = user32.GetDC(0)
            hdc_mem = gdi32.CreateCompatibleDC(hdc)
            
            bi = BITMAPINFOHEADER()
            bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bi.biWidth = width
            bi.biHeight = -height  # 负数表示自上而下
            bi.biPlanes = 1
            bi.biBitCount = 32
            bi.biCompression = 0  # BI_RGB
            
            # 分配缓冲区
            buffer_size = width * height * 4
            buffer = ctypes.create_string_buffer(buffer_size)
            
            # 获取像素数据
            gdi32.GetDIBits(
                hdc_mem, hbitmap, 0, height,
                buffer, ctypes.byref(bi), 0  # DIB_RGB_COLORS
            )
            
            # 清理 GDI 资源
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc)
            gdi32.DeleteObject(hbitmap)
            
            # 释放 COM 对象
            ReleaseProto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
            Release = ReleaseProto(vtable[2])
            Release(shell_item)
            
            # 转换为 PIL Image (BGRA -> RGBA)
            img = Image.frombuffer('RGBA', (width, height), buffer.raw, 'raw', 'BGRA', 0, 1)
            
            # 输出为 PNG
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
            
        finally:
            ole32.CoUninitialize()
            
    except ImportError as e:
        print(f"缺少依赖: {e}")
        return None
    except Exception as e:
        print(f"获取系统缩略图失败: {e}")
        return None


@router.get("/file")
async def serve_file(
    path: str = Query(..., description="本地文件路径"),
    thumbnail: bool = Query(False, description="是否返回系统缩略图"),
    size: int = Query(128, description="缩略图尺寸")
):
    """
    提供本地文件访问
    
    用于前端显示本地图片、视频等资源
    例如: /v1/file?path=E:/video.mp4&thumbnail=true
    
    thumbnail=true 时返回 Windows 资源管理器的系统缩略图
    """
    file_path = Path(path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"不是文件: {path}")
    
    # 请求系统缩略图
    if thumbnail:
        thumb_data = _get_windows_thumbnail(str(file_path.resolve()), size)
        if thumb_data:
            return Response(content=thumb_data, media_type="image/png")
        raise HTTPException(status_code=500, detail="无法获取系统缩略图")
    
    # 普通文件访问
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"
    
    return FileResponse(path=file_path, media_type=mime_type, filename=file_path.name)


@router.get("/preview/{workshop_id}")
async def get_wallpaper_preview(
    workshop_id: str,
    workshop_path: str = Query(..., description="工坊根目录路径")
):
    """获取壁纸预览图"""
    workshop_dir = Path(workshop_path)
    wallpaper_dir = workshop_dir / workshop_id
    
    if not wallpaper_dir.exists():
        raise HTTPException(status_code=404, detail=f"壁纸目录不存在: {workshop_id}")
    
    for name in ["preview.gif", "preview.jpg", "preview.png", "preview.webp"]:
        preview_path = wallpaper_dir / name
        if preview_path.exists():
            mime_type, _ = mimetypes.guess_type(str(preview_path))
            return FileResponse(path=preview_path, media_type=mime_type or "image/gif")
    
    raise HTTPException(status_code=404, detail=f"未找到预览图: {workshop_id}")
