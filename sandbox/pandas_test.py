import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

from database import connect

connection, cursor = connect()

df = pd.read_sql_query("""select 
	project.name, project.id, project.start_date, project.end_date, 
    (
    	select count(*) from task left outer join task_status on task.task_status_id = task_status.id where task.project_id = project.id
    ) as total_tasks,
    (
    	select count(*) from task left outer join task_status on task.task_status_id = task_status.id where task.project_id = project.id and task_status.is_done
    ) as completed_tasks
    
from
	project   
group by project.name, project.id;
;""", con=connection)
#print(df)

df = df.assign(perc_done=lambda x: x.completed_tasks / x.total_tasks * 100)
print(df)

##df1 = df.assign(Discount_Percent=lambda x: x.Discount / x.Fee * 100)
##df.plot(kind="bar")

def create_gantt_chart(updated_table_as_df):
    gantt_fig = px.timeline(
        updated_table_as_df,
        x_start="start_date",
        x_end="end_date",
        y="name",
        color="perc_done",
        title="WCA | CG | Project Completion",
    )

    gantt_fig.update_layout(
        title_x=0.5,
        font=dict(size=16),
        yaxis=dict(
            title="Projects",
            automargin=True,
            autorange="reversed",
            categoryorder="array",
            categoryarray=updated_table_as_df["perc_done"],
        ),  # sorting gantt according to datatable
        xaxis=dict(title=""),
    )
    gantt_fig.update_traces(width=0.7)
    return gantt_fig

fig = create_gantt_chart(df)
##fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
fig.show()