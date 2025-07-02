from io import BytesIO
from fastapi import HTTPException, UploadFile
import pandas as pd


async def read_excel(file: UploadFile) -> pd.DataFrame:
    """Reads an uploaded CSV or Excel file and returns a DataFrame."""
    contents = await file.read()

    if file.filename.endswith(".csv"):
        df = pd.read_csv(BytesIO(contents))
    elif file.filename.endswith((".xls", ".xlsx")):
        df = pd.read_excel(BytesIO(contents))
    else:
        raise HTTPException(400, "Unsupportedd file format")
    return df
