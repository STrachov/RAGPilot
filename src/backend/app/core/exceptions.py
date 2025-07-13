class RAGPilotError(Exception):
    """Base exception for the RAGPilot application."""
    pass

class TaskNotFoundError(RAGPilotError):
    """Raised when a task ID is not found in the processing service (e.g., RAGParser)."""
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task with ID '{task_id}' was not found. It may have been completed and cleaned up.")
