"""optimize_documents_table_structure

Revision ID: a27b7e62850d
Revises: add_settings_table
Create Date: 2025-06-18 20:21:01.361210

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import json
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'a27b7e62850d'
down_revision = 'add_settings_table'
branch_labels = None
depends_on = None


def upgrade():
    """Add new columns and migrate data from redundant fields"""
    
    # Add new optimized columns
    op.add_column('documents', sa.Column('binary_hash', sa.String(64), nullable=True))
    op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True))
    
    # Create indexes for the new columns (for performance)
    op.create_index('ix_documents_binary_hash', 'documents', ['binary_hash'])
    op.create_index('ix_documents_page_count', 'documents', ['page_count'])
    
    # Migrate data from redundant columns to status/metadata JSON
    connection = op.get_bind()
    
    # Get all documents
    documents = connection.execute(sa.text("SELECT id, status, metadata, parse_config, ragparser_task_id FROM documents")).fetchall()
    
    for doc in documents:
        doc_id, status_json, metadata_json, parse_config_json, ragparser_task_id = doc
        
        # Parse existing JSON fields
        try:
            status_dict = json.loads(status_json) if status_json else {"stages": {}}
        except (json.JSONDecodeError, TypeError):
            status_dict = {"stages": {}}
            
        try:
            metadata_dict = json.loads(metadata_json) if metadata_json else {}
        except (json.JSONDecodeError, TypeError):
            metadata_dict = {}
        
        # Migrate parse_config to status.stages.parse.config if not already there
        if parse_config_json and "stages" in status_dict and "parse" in status_dict["stages"]:
            try:
                parse_config = json.loads(parse_config_json)
                if "config" not in status_dict["stages"]["parse"]:
                    status_dict["stages"]["parse"]["config"] = parse_config
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Migrate ragparser_task_id to status.stages.parse.ragparser_task_id if not already there
        if ragparser_task_id and "stages" in status_dict and "parse" in status_dict["stages"]:
            if "ragparser_task_id" not in status_dict["stages"]["parse"]:
                status_dict["stages"]["parse"]["ragparser_task_id"] = ragparser_task_id
        
        # Clean up metadata from processing-related data, keep only static document characteristics
        clean_metadata = {}
        for key, value in metadata_dict.items():
            # Keep only non-processing metadata
            if key in ["uploaded_by", "original_filename"]:
                clean_metadata[key] = value
            # Remove processing-related metadata that should be in status
            elif key not in ["ragparser_task_id", "ragparser_progress", "ragparser_state", 
                           "parsing_started_at", "parsed_at", "parsing_completed", 
                           "last_status_check", "queue_position"]:
                clean_metadata[key] = value
        
        # Update the document with cleaned data
        connection.execute(
            sa.text("UPDATE documents SET status = :status, metadata = :metadata WHERE id = :id"),
            {
                "id": doc_id,
                "status": json.dumps(status_dict),
                "metadata": json.dumps(clean_metadata) if clean_metadata else None
            }
        )


def downgrade():
    """Remove new columns and restore redundant fields (partial rollback)"""
    
    # Drop indexes
    op.drop_index('ix_documents_page_count', 'documents')
    op.drop_index('ix_documents_binary_hash', 'documents')
    
    # Drop new columns
    op.drop_column('documents', 'page_count')
    op.drop_column('documents', 'binary_hash')
    
    # Note: We don't restore parse_config and ragparser_task_id columns here
    # as they would need to be migrated back from the JSON, which is complex
    # and not typically needed. If rollback is required, it should be done
    # with a separate migration that handles the data migration properly.
