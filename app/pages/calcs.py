import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter and add it to the handler
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)

import pandas as pd



'''
=IF(AND(M3<>"todo",K3<>"",N3<>"",N3<=K3),"Started | On Time | Scheduled",IF(AND(M3<>"todo",K3<>"",N3<>"",N3>K3),"Started | LATE | Scheduled",IF(AND(M3<>"todo",K3<>"",N3="",K3>TODAY()),"Not Started | Overdue | Scheduled",IF(AND(M3="todo",M3<>"final",K3<>"",N3="",K3>TODAY()),"Not Started | Due | Scheduled","NO SCHEDULE START DATE"))))
'''

def get_status_description(row: pd.Series) -> str:
    """
    This function returns a status description of the task 
    """
    task_activity = row["task_status"] != 'Todo'

    ##logging.debug(f"task_activity: {task_activity} {row['task_status']}")
    ##logging.debug(row)
    
    task_late = row["task_real_start_date"] > row["task_start_date"]
    is_overdue = row["task_due_date"] < row["task_end_date"]

    if task_activity:
        if not row["task_real_start_date"]:
            return "Started | No Start Date"

    if task_activity and not task_late and not is_overdue:
        return "Started | On Time | Scheduled"

    if task_activity and task_late and not is_overdue:
        return "Started | LATE | Scheduled"

    if task_activity and not task_late and is_overdue:
        return "Not Started | Overdue | Scheduled"
    
    if task_activity:
        return "Started | Not Scheduled"

    return "No Info"