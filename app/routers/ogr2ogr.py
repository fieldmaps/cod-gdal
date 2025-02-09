from asyncio import create_subprocess_exec
from os import getenv
from pathlib import Path
from tempfile import TemporaryDirectory

# from typing import Annotated
# from fastapi import APIRouter, HTTPException, Query, status
from fastapi import APIRouter, HTTPException, status

S3_ASSETS_BUCKET = getenv("S3_ASSETS_BUCKET", "")
S3_CACHE_BUCKET = getenv("S3_CACHE_BUCKET", "")
S3_CHUNK_SIZE = getenv("S3_CHUNK_SIZE", "")

router = APIRouter()


def get_recommended_options(local_format: str) -> list[str]:
    """Get recommended options for output formats."""
    match local_format:
        case "shp.zip":
            return ["-lco", "ENCODING=UTF-8"]
        case _:
            return []


def get_local_format(local_format: str) -> str:
    """Remove .zip from formats outputing to directory and add .zip to shapefiles."""
    if local_format == "gdb.zip":
        return local_format.rstrip(".zip")
    if local_format == "shp":
        return f"{local_format}.zip"
    return local_format


def get_remote_format(remote_format: str) -> str:
    """Add .zip to formats outputing to directory."""
    if remote_format in ["shp", "gdb"]:
        return f"{remote_format}.zip"
    return remote_format


@router.get(
    "/ogr2ogr/{processing_level}/{iso3}/{admin_level}",
    description="Get vector in any GDAL/OGR supported format",
    tags=["vectors"],
)
async def features(
    processing_level: str,
    iso3: str,
    admin_level: int,
    f: str = "geojson",
    # simplify: str | None = None,
    # lco: Annotated[list[str] | None, Query()] = None,
) -> str:
    """Convert features to other file format.

    Returns:
        Converted File.
    """
    f = f.lower().lstrip(".")
    if f == "parquet":
        return "ok"
    processing_level = processing_level.lower()
    layer = f"{iso3}_adm{admin_level}".lower()
    local_format = get_local_format(f)
    remote_format = get_remote_format(f)
    assets_bucket = f"{S3_ASSETS_BUCKET}/level-{processing_level}/{layer}.parquet"
    cache_bucket = f"{S3_CACHE_BUCKET}/level-{processing_level}/{layer}.{remote_format}"
    recommended_options = get_recommended_options(local_format)
    # lco_options = [("-lco", x) for x in lco] if lco is not None else []
    # simplify_options = ["-simplify", simplify] if simplify is not None else []
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / f"{layer}.parquet"
        output_path = Path(tmp) / f"{layer}.{local_format}"
        rclone_download = await create_subprocess_exec(
            "rclone",
            "copyto",
            *["--s3-chunk-size", S3_CHUNK_SIZE],
            assets_bucket,
            input_path,
        )
        await rclone_download.wait()
        ogr2ogr = await create_subprocess_exec(
            "ogr2ogr",
            "-overwrite",
            *["--config", "GDAL_NUM_THREADS", "ALL_CPUS"],
            *["--config", "OGR_GEOJSON_MAX_OBJ_SIZE", "0"],
            *["--config", "OGR_ORGANIZE_POLYGONS", "ONLY_CCW"],
            *["-nln", layer],
            # *simplify_options,
            # *[x for y in lco_options for x in y],
            *recommended_options,
            output_path,
            input_path,
        )
        await ogr2ogr.wait()
        if output_path.stat().st_size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unprocessable Content",
            )
        if output_path.is_dir():
            output_zip = output_path.with_suffix(f".{f}.zip")
            sozip = await create_subprocess_exec(
                "sozip",
                "-r",
                output_zip,
                output_path,
            )
            await sozip.wait()
            output_path = output_zip
        rclone_upload = await create_subprocess_exec(
            "rclone",
            "copyto",
            *["--s3-chunk-size", S3_CHUNK_SIZE],
            output_path,
            cache_bucket,
        )
        await rclone_upload.wait()
    return "ok"
