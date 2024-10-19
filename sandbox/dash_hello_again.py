from dash import Dash, html, dash_table
import pandas as pd

from database import connect, close

app = Dash()

def load_layout(app):
    app.layout = [html.Div(children='Hello World')]
    return app

def load_data():
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

if __name__ == '__main__':
    app = load_layout(app)
    app.run(debug=False)