from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd

from database import connect

connection, cursor = connect()

df = pd.read_sql_query("""select project.name, project.id, project.start_date, project.end_date, count(task) from project
left outer join task on task.project_id = project.id
group by project.name, project.id;""", con=connection)

app = Dash()

app.layout = [
    html.H1(children='Title of Dash App', style={'textAlign':'center'}),
    dcc.Dropdown(df.name.unique(), 'Project', id='dropdown-selection'),
    dcc.Graph(id='graph-content')
]

@callback(
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph(value):
    dff = df[df.name==value]

    fig = px.timeline(dff, x_start="start_date", x_end="end_date", y="name")
    fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up    

    return fig

if __name__ == '__main__':
    app.run(debug=False)