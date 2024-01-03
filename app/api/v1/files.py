import io
import os
import urllib.parse
from typing import Optional, List

from fastapi import APIRouter, Depends, UploadFile, Form, HTTPException, Query
from sqlmodel import Session
from starlette.responses import StreamingResponse

from app.api.deps import get_session
from app.models import File
from app.schemas.common import DeleteResponse
from app.schemas.files import ListFilesResponse
from app.services.file.file import FileService

router = APIRouter()

# 限制文件大小
max_size = 512 * 1024 * 1024
# 支持的文件类型
file_ext = [".txt", ".md", ".pdf", ".html"]


@router.get("", response_model=ListFilesResponse)
def list_files(
    *,
    purpose: Optional[str] = None,
    file_ids: Optional[List[str]] = Query(None, alias="ids[]"),
    session: Session = Depends(get_session),
) -> ListFilesResponse:
    """
    Returns a list of files that belong to the user's organization.
    """
    files = FileService.get_file_list(session=session, purpose=purpose, file_ids=file_ids)
    return ListFilesResponse(data=files)


@router.post("", response_model=File)
def create_file(
    *, session: Session = Depends(get_session), purpose: str = Form(default="assistants"), file: UploadFile
) -> File:
    """
    The size of individual files can be a maximum of 512 MB. See the [Assistants Tools guide]
    (/docs/assistants/tools) to learn more about the types of files supported.
    """
    # 判断后缀名
    _, file_extension = os.path.splitext(file.filename)
    if file_extension not in file_ext:
        raise HTTPException(status_code=400, detail=f"文件类型{file_extension}暂时不支持")
    # 判断文件大小
    if file.size == 0 or file.size > max_size:
        raise HTTPException(status_code=413, detail="File too large")

    return FileService.create_file(session=session, purpose=purpose, file=file)


@router.delete("/{file_id}", response_model=DeleteResponse)
def delete_file(*, session: Session = Depends(get_session), file_id: str) -> DeleteResponse:
    """
    Delete a file.
    """
    return FileService.delete_file(session=session, file_id=file_id)


@router.get("/{file_id}", response_model=File)
def retrieve_file(*, session: Session = Depends(get_session), file_id: str) -> File:
    """
    Returns information about a specific file.
    """
    return FileService.get_file(session=session, file_id=file_id)


@router.get("/{file_id}/content", response_class=StreamingResponse)
def download_file(*, file_id: str, session: Session = Depends(get_session)):
    """
    Returns the contents of the specified file.
    """
    file_data, filename = FileService.get_file_content(session=session, file_id=file_id)

    response = StreamingResponse(io.BytesIO(file_data), media_type="application/octet-stream")
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    response.headers["Content-Type"] = "application/octet-stream"
    return response
