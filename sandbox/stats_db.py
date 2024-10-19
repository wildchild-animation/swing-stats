from database import connect, close

if __name__ == "__main__":
    print("Connecting to Database")
    connection, cursor = connect()
    try:
        print("Connected to Database") 
    finally:
        close(connection) 
        print("Connection Closed")


