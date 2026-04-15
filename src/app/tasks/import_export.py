"""Celery tasks for async document export and import execution.

Export: Builds ZIP with manifest.json, document content, folder hierarchy, ACLs, relationships.
Import: Reads ZIP, creates folders/documents with conflict resolution (skip/overwrite/rename).
"""
import asyncio
import hashlib
import io
import json
import logging
import uuid
import zipfile
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.import_export.execute_export_job",
    bind=True,
    max_retries=1,
)
def execute_export_job(self, job_id: str):
    """Execute an export job asynchronously via Celery."""
    try:
        asyncio.run(_execute_export_async(job_id))
    except Exception as exc:
        logger.error("Export job %s failed: %s", job_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.import_export.execute_import_job",
    bind=True,
    max_retries=1,
)
def execute_import_job(self, job_id: str):
    """Execute an import job asynchronously via Celery."""
    try:
        asyncio.run(_execute_import_async(job_id))
    except Exception as exc:
        logger.error("Import job %s failed: %s", job_id, exc)
        raise self.retry(exc=exc)


async def _execute_export_async(job_id: str):
    """Async implementation of export job."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.database import create_task_session_factory
    from app.core.minio_client import download_object, upload_object
    from app.models.acl import DocumentACL, FolderACL
    from app.models.bulk_job import BulkJob
    from app.models.document import Document, DocumentVersion
    from app.models.document_relationship import DocumentRelationship
    from app.models.folder import Folder, document_folders

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # Load the job
        result = await session.execute(
            select(BulkJob).where(BulkJob.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if job is None:
            logger.warning("Export job %s not found, skipping", job_id)
            return

        job.status = "running"
        await session.flush()

        results = []
        success_count = 0
        failure_count = 0

        # Collect all document IDs
        all_doc_ids = set()
        for did in job.document_ids:
            all_doc_ids.add(uuid.UUID(did))

        # Collect folder IDs and recursively find documents
        folder_ids_to_export = set()
        raw_folder_ids = (job.parameters or {}).get("folder_ids", [])
        folders_to_process = [uuid.UUID(fid) for fid in raw_folder_ids]

        while folders_to_process:
            fid = folders_to_process.pop()
            folder_ids_to_export.add(fid)
            # Get documents in this folder
            df_result = await session.execute(
                select(document_folders.c.document_id).where(
                    document_folders.c.folder_id == fid
                )
            )
            for row in df_result:
                all_doc_ids.add(row[0])
            # Get child folders
            child_result = await session.execute(
                select(Folder.id).where(Folder.parent_id == fid)
            )
            for row in child_result:
                folders_to_process.append(row[0])

        include_acls = (job.parameters or {}).get("include_acls", True)
        include_rels = (job.parameters or {}).get("include_relationships", True)

        # Build manifest
        manifest = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": job.created_by,
            "documents": [],
            "folders": [],
            "folder_filings": [],
            "acls": {"documents": [], "folders": []},
            "relationships": [],
        }

        # ZIP buffer
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Export documents
            for doc_id in all_doc_ids:
                try:
                    doc_result = await session.execute(
                        select(Document)
                        .options(selectinload(Document.versions))
                        .where(Document.id == doc_id)
                    )
                    doc = doc_result.scalar_one_or_none()
                    if doc is None:
                        results.append({"document_id": str(doc_id), "status": "error", "error": "Not found"})
                        failure_count += 1
                        continue

                    # Get latest version
                    latest_version = None
                    for v in doc.versions:
                        if latest_version is None or (v.major_version, v.minor_version) > (latest_version.major_version, latest_version.minor_version):
                            latest_version = v

                    content_file = f"docs/{doc.id}/{doc.filename}"
                    if latest_version and latest_version.minio_object_key:
                        try:
                            content = await download_object(latest_version.minio_object_key)
                            zf.writestr(content_file, content)
                        except Exception as e:
                            logger.warning("Could not download content for doc %s: %s", doc.id, e)
                            content_file = ""

                    manifest["documents"].append({
                        "id": str(doc.id),
                        "title": doc.title,
                        "author": doc.author,
                        "filename": doc.filename,
                        "content_type": doc.content_type,
                        "custom_properties": doc.custom_properties or {},
                        "lifecycle_state": doc.lifecycle_state,
                        "document_type_id": str(doc.document_type_id) if doc.document_type_id else None,
                        "content_file": content_file,
                        "version": {
                            "major": doc.current_major_version,
                            "minor": doc.current_minor_version,
                        },
                    })

                    results.append({"document_id": str(doc_id), "status": "success"})
                    success_count += 1
                except Exception as e:
                    results.append({"document_id": str(doc_id), "status": "error", "error": str(e)})
                    failure_count += 1
                    logger.warning("Export doc %s failed: %s", doc_id, e)

            # Export folders
            for fid in folder_ids_to_export:
                folder_result = await session.execute(
                    select(Folder).where(Folder.id == fid)
                )
                folder = folder_result.scalar_one_or_none()
                if folder:
                    manifest["folders"].append({
                        "id": str(folder.id),
                        "name": folder.name,
                        "parent_id": str(folder.parent_id) if folder.parent_id else None,
                        "is_cabinet": folder.is_cabinet,
                        "description": folder.description,
                    })

            # Export folder filings
            if folder_ids_to_export:
                ff_result = await session.execute(
                    select(document_folders).where(
                        document_folders.c.folder_id.in_(folder_ids_to_export)
                    )
                )
                for row in ff_result:
                    manifest["folder_filings"].append({
                        "document_id": str(row.document_id),
                        "folder_id": str(row.folder_id),
                    })

            # Export ACLs
            if include_acls and all_doc_ids:
                doc_acl_result = await session.execute(
                    select(DocumentACL).where(DocumentACL.document_id.in_(all_doc_ids))
                )
                for acl in doc_acl_result.scalars():
                    manifest["acls"]["documents"].append({
                        "document_id": str(acl.document_id),
                        "principal_id": str(acl.principal_id),
                        "principal_type": acl.principal_type,
                        "permission_level": acl.permission_level,
                    })

            if include_acls and folder_ids_to_export:
                folder_acl_result = await session.execute(
                    select(FolderACL).where(FolderACL.folder_id.in_(folder_ids_to_export))
                )
                for acl in folder_acl_result.scalars():
                    manifest["acls"]["folders"].append({
                        "folder_id": str(acl.folder_id),
                        "principal_id": str(acl.principal_id),
                        "principal_type": acl.principal_type,
                        "permission_level": acl.permission_level,
                    })

            # Export relationships
            if include_rels and all_doc_ids:
                rel_result = await session.execute(
                    select(DocumentRelationship).where(
                        DocumentRelationship.source_document_id.in_(all_doc_ids)
                    )
                )
                for rel in rel_result.scalars():
                    manifest["relationships"].append({
                        "source_document_id": str(rel.source_document_id),
                        "target_document_id": str(rel.target_document_id),
                        "relationship_type": rel.relationship_type,
                        "description": rel.description,
                    })

            # Write manifest.json to ZIP
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Upload completed ZIP to MinIO
        zip_data = zip_buf.getvalue()
        zip_object_key = f"exports/{job_id}.zip"
        await upload_object(zip_object_key, zip_data, "application/zip")

        # Finalize job
        job.results = results
        job.success_count = success_count
        job.failure_count = failure_count
        job.total_count = success_count + failure_count
        job.completed_at = datetime.now(timezone.utc)
        job.status = "failed" if failure_count == job.total_count and job.total_count > 0 else "completed"
        if job.parameters is None:
            job.parameters = {}
        job.parameters = {**job.parameters, "zip_object_key": zip_object_key}

        await session.commit()
        logger.info("Export job %s finished: %d success, %d failed", job_id, success_count, failure_count)


async def _execute_import_async(job_id: str):
    """Async implementation of import job."""
    from sqlalchemy import select

    from app.core.database import create_task_session_factory
    from app.core.minio_client import delete_object, download_object, upload_object
    from app.models.acl import DocumentACL, FolderACL
    from app.models.bulk_job import BulkJob
    from app.models.document import Document, DocumentVersion
    from app.models.document_relationship import DocumentRelationship
    from app.models.folder import Folder, document_folders

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # Load the job
        result = await session.execute(
            select(BulkJob).where(BulkJob.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if job is None:
            logger.warning("Import job %s not found, skipping", job_id)
            return

        job.status = "running"
        await session.flush()

        results = []
        success_count = 0
        failure_count = 0

        params = job.parameters or {}
        zip_key = params.get("zip_key", "")
        target_folder_id = params.get("target_folder_id")
        conflict_strategy = params.get("conflict_strategy", "skip")

        try:
            # Download ZIP from MinIO
            zip_data = await download_object(zip_key)
            zip_buf = io.BytesIO(zip_data)

            with zipfile.ZipFile(zip_buf, "r") as zf:
                # Parse manifest
                manifest_data = zf.read("manifest.json")
                manifest = json.loads(manifest_data)

                doc_entries = manifest.get("documents", [])
                folder_entries = manifest.get("folders", [])
                folder_filings = manifest.get("folder_filings", [])
                acl_data = manifest.get("acls", {"documents": [], "folders": []})
                relationship_entries = manifest.get("relationships", [])

                job.total_count = len(doc_entries)
                await session.flush()

                # Phase 1: Create folders -- map old IDs to new UUIDs
                folder_id_map = {}  # old_id -> new_id
                if folder_entries:
                    # Sort by parent-first order
                    created_set = set()
                    remaining = list(folder_entries)
                    max_iterations = len(remaining) * 2
                    iteration = 0
                    while remaining and iteration < max_iterations:
                        iteration += 1
                        for entry in list(remaining):
                            old_id = entry["id"]
                            parent_old = entry.get("parent_id")

                            # Determine new parent
                            if parent_old is None:
                                new_parent = uuid.UUID(target_folder_id) if target_folder_id else None
                            elif parent_old in folder_id_map:
                                new_parent = folder_id_map[parent_old]
                            else:
                                continue  # Parent not created yet

                            new_folder = Folder(
                                id=uuid.uuid4(),
                                name=entry["name"],
                                description=entry.get("description"),
                                parent_id=new_parent,
                                is_cabinet=entry.get("is_cabinet", False),
                            )
                            session.add(new_folder)
                            await session.flush()
                            folder_id_map[old_id] = new_folder.id
                            created_set.add(old_id)
                            remaining.remove(entry)

                # Phase 2: Create documents with conflict resolution
                doc_id_map = {}  # old_id -> new_id
                for doc_entry in doc_entries:
                    try:
                        old_doc_id = doc_entry["id"]
                        title = doc_entry["title"]
                        filename = doc_entry.get("filename", "unknown")
                        content_type = doc_entry.get("content_type", "application/octet-stream")

                        # Check for conflict
                        existing_result = await session.execute(
                            select(Document).where(Document.title == title)
                        )
                        existing = existing_result.scalar_one_or_none()

                        if existing and conflict_strategy == "skip":
                            results.append({
                                "document_id": old_doc_id,
                                "status": "skipped",
                                "reason": "duplicate title",
                            })
                            doc_id_map[old_doc_id] = existing.id
                            success_count += 1
                            continue
                        elif existing and conflict_strategy == "overwrite":
                            # Update existing document metadata
                            existing.author = doc_entry.get("author")
                            existing.content_type = content_type
                            existing.custom_properties = doc_entry.get("custom_properties", {})
                            doc = existing
                        elif existing and conflict_strategy == "rename":
                            title = f"{title} (imported)"
                            doc = Document(
                                id=uuid.uuid4(),
                                title=title,
                                author=doc_entry.get("author"),
                                filename=filename,
                                content_type=content_type,
                                custom_properties=doc_entry.get("custom_properties", {}),
                                current_major_version=doc_entry.get("version", {}).get("major", 0),
                                current_minor_version=doc_entry.get("version", {}).get("minor", 1),
                            )
                            session.add(doc)
                        else:
                            # No conflict -- create new
                            doc = Document(
                                id=uuid.uuid4(),
                                title=title,
                                author=doc_entry.get("author"),
                                filename=filename,
                                content_type=content_type,
                                custom_properties=doc_entry.get("custom_properties", {}),
                                current_major_version=doc_entry.get("version", {}).get("major", 0),
                                current_minor_version=doc_entry.get("version", {}).get("minor", 1),
                            )
                            session.add(doc)

                        await session.flush()
                        doc_id_map[old_doc_id] = doc.id

                        # Upload content from ZIP to MinIO
                        content_file = doc_entry.get("content_file", "")
                        if content_file and content_file in zf.namelist():
                            content = zf.read(content_file)
                            content_hash = hashlib.sha256(content).hexdigest()
                            minio_key = f"docs/{doc.id}/{filename}"
                            await upload_object(minio_key, content, content_type)

                            # Create version record
                            version = DocumentVersion(
                                id=uuid.uuid4(),
                                document_id=doc.id,
                                major_version=doc_entry.get("version", {}).get("major", 0),
                                minor_version=doc_entry.get("version", {}).get("minor", 1),
                                content_hash=content_hash,
                                content_size=len(content),
                                minio_object_key=minio_key,
                                filename=filename,
                                content_type=content_type,
                            )
                            session.add(version)
                            await session.flush()

                        results.append({"document_id": old_doc_id, "status": "success", "new_id": str(doc.id)})
                        success_count += 1
                    except Exception as e:
                        results.append({"document_id": doc_entry.get("id", "unknown"), "status": "error", "error": str(e)})
                        failure_count += 1
                        logger.warning("Import doc %s failed: %s", doc_entry.get("id"), e)

                # Phase 3: File documents into folders
                for filing in folder_filings:
                    old_doc_id = filing["document_id"]
                    old_folder_id = filing["folder_id"]
                    new_doc_id = doc_id_map.get(old_doc_id)
                    new_folder_id = folder_id_map.get(old_folder_id)
                    if new_doc_id and new_folder_id:
                        try:
                            await session.execute(
                                document_folders.insert().values(
                                    document_id=new_doc_id,
                                    folder_id=new_folder_id,
                                    filed_by=job.created_by,
                                )
                            )
                        except Exception as e:
                            logger.warning("Filing doc %s into folder %s failed: %s", old_doc_id, old_folder_id, e)

                # Phase 4: Recreate ACLs
                for acl_entry in acl_data.get("documents", []):
                    new_doc_id = doc_id_map.get(acl_entry["document_id"])
                    if new_doc_id:
                        try:
                            acl = DocumentACL(
                                id=uuid.uuid4(),
                                document_id=new_doc_id,
                                principal_id=uuid.UUID(acl_entry["principal_id"]),
                                principal_type=acl_entry["principal_type"],
                                permission_level=acl_entry["permission_level"],
                            )
                            session.add(acl)
                        except Exception as e:
                            logger.warning("Import doc ACL failed: %s", e)

                for acl_entry in acl_data.get("folders", []):
                    new_folder_id = folder_id_map.get(acl_entry["folder_id"])
                    if new_folder_id:
                        try:
                            acl = FolderACL(
                                id=uuid.uuid4(),
                                folder_id=new_folder_id,
                                principal_id=uuid.UUID(acl_entry["principal_id"]),
                                principal_type=acl_entry["principal_type"],
                                permission_level=acl_entry["permission_level"],
                            )
                            session.add(acl)
                        except Exception as e:
                            logger.warning("Import folder ACL failed: %s", e)

                # Phase 5: Recreate relationships
                for rel_entry in relationship_entries:
                    src_id = doc_id_map.get(rel_entry["source_document_id"])
                    tgt_id = doc_id_map.get(rel_entry["target_document_id"])
                    if src_id and tgt_id:
                        try:
                            rel = DocumentRelationship(
                                id=uuid.uuid4(),
                                source_document_id=src_id,
                                target_document_id=tgt_id,
                                relationship_type=rel_entry["relationship_type"],
                                description=rel_entry.get("description"),
                            )
                            session.add(rel)
                        except Exception as e:
                            logger.warning("Import relationship failed: %s", e)

                await session.flush()

        except Exception as e:
            logger.error("Import job %s failed globally: %s", job_id, e)
            job.status = "failed"
            job.results = [{"status": "error", "error": str(e)}]
            await session.commit()
            return

        # Finalize job
        job.results = results
        job.success_count = success_count
        job.failure_count = failure_count
        job.completed_at = datetime.now(timezone.utc)
        job.status = "failed" if failure_count == job.total_count and job.total_count > 0 else "completed"

        await session.commit()

        # Clean up temp ZIP
        try:
            await delete_object(zip_key)
        except Exception as e:
            logger.warning("Could not delete temp ZIP %s: %s", zip_key, e)

        logger.info("Import job %s finished: %d success, %d failed", job_id, success_count, failure_count)
