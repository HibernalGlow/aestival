"""
备份服务 API - 提供文件备份相关操作
替代 Tauri invoke 调用
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
from typing import List, Optional
import fnmatch

router = APIRouter(prefix="/backup", tags=["backup"])


class CreateDirectoryRequest(BaseModel):
    path: str


class WriteFileRequest(BaseModel):
    path: str
    content: str


class ReadFileRequest(BaseModel):
    path: str


class DeleteFileRequest(BaseModel):
    path: str


class ListFilesRequest(BaseModel):
    path: str
    pattern: Optional[str] = None


class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    modified: float


@router.post("/create-directory")
async def create_directory(request: CreateDirectoryRequest):
    """创建目录"""
    try:
        path = Path(request.path)
        path.mkdir(parents=True, exist_ok=True)
        return {"success": True, "path": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write-file")
async def write_text_file(request: WriteFileRequest):
    """写入文本文件"""
    try:
        path = Path(request.path)
        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(request.content, encoding="utf-8")
        return {"success": True, "path": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read-file")
async def read_text_file(request: ReadFileRequest):
    """读取文本文件"""
    try:
        path = Path(request.path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {request.path}")
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"不是文件: {request.path}")
        content = path.read_text(encoding="utf-8")
        return {"success": True, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-file")
async def delete_file(request: DeleteFileRequest):
    """删除文件"""
    try:
        path = Path(request.path)
        if path.exists() and path.is_file():
            path.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list-files")
async def list_directory_files(request: ListFilesRequest) -> List[FileInfo]:
    """列出目录中的文件"""
    try:
        path = Path(request.path)
        if not path.exists():
            return []
        if not path.is_dir():
            raise HTTPException(status_code=400, detail=f"不是目录: {request.path}")
        
        files = []
        for item in path.iterdir():
            if item.is_file():
                # 如果有 pattern，进行匹配
                if request.pattern and not fnmatch.fnmatch(item.name, request.pattern):
                    continue
                stat = item.stat()
                files.append(FileInfo(
                    name=item.name,
                    path=str(item),
                    size=stat.st_size,
                    modified=stat.st_mtime * 1000  # 转换为毫秒时间戳
                ))
        return files
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/default-path")
async def get_default_backup_path():
    """获取默认备份路径"""
    try:
        # 使用用户数据目录
        if os.name == "nt":  # Windows
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            default_path = Path(app_data) / "aestivus" / "backups"
        else:  # Linux/Mac
            default_path = Path.home() / ".local" / "share" / "aestivus" / "backups"
        
        # 确保目录存在
        default_path.mkdir(parents=True, exist_ok=True)
        
        return {"success": True, "path": str(default_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
