import logging
import datetime
import traceback

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

def load_default_calcs(df: pd.DataFrame) -> str:

    # Calculate duration in days
    df = df.assign(
        calc_duration=lambda x: (
            (pd.to_datetime(x.task_end_date) - pd.to_datetime(x.task_start_date)) / pd.Timedelta(days=1)
        ).round(2)
    )

    ## estimate is stored in minutes, convert to days
    df = df.assign(
        calc_estimate=lambda x: (x.task_estimation / 60 / 8).round(2),
    )

    # Status Description
    df["status_description"] = df.apply(lambda row: get_status_description(row), axis=1)  
    df["calc_status_color"] = df.apply(lambda row: get_status_color(row), axis=1)      

    df["calc_task_real_start_date"] = df.apply(lambda row: str_parse_date(row['task_real_start_date']), axis=1)  
    df["calc_task_end_date"] = df.apply(lambda row: str_parse_date(row['task_end_date']), axis=1)  
    df["calc_task_start_date"] = df.apply(lambda row: str_parse_date(row['task_start_date']), axis=1)  
    df["calc_task_due_date"] = df.apply(lambda row: str_parse_date(row['task_due_date']), axis=1)              

    # Standarise dates
    #df = df.assign(calc_task_real_start_date = lambda x: str_parse_date(x['task_real_start_date']), axis=1)

    df.reindex()
    return df



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

def get_status_color(row: pd.Series) -> str:
    """
    Returns a color based on the status of the task
    """

    """
    This function returns a status description of the task 
    """
    status_description = row["status_description"]

    if "late" in status_description.lower():
        return "red"
    
    if "on time" in status_description.lower():
        return "green"
    
    if "overdue" in status_description.lower():
        return "red"
    
    if "not scheduled" in status_description.lower():
        return "yellow"
    
    return "grey"

def str_parse_date(date_item):
    date = ""    

    if not date_item:
        return date
    
    if "NaT" in str(date_item):
        return date
    
    if isinstance(date_item, datetime.datetime):
        return date_item.strftime('%e %b %Y')
    
    if len(date_item) == 19 and "T" in date_item:
        date = datetime.strptime(date_item, "%Y-%m-%dT%H:%M:%S")
    elif len(date_item) == 10 and "-" in date_item:
        date = datetime.strptime(date_item, "%Y-%m-%d")
    elif "," in date_item:
        date = datetime.strptime(date_item, "%A, %d %B %Y")
    else:
        try:
            date = datetime.strptime(date_item, "%Y-%m-%dT%H:%M:%S")
        except:
            traceback.print_exc()
            return "NaNa"
    date = date_item.strftime("%Y-%m-%d")        

    return date    