import sqlite3

print("Building database... Please wait, this might take a few moments.")
try:
    # Connect to the database file (it will be created if it doesn't exist)
    conn = sqlite3.connect("dictionary.db")
    cursor = conn.cursor()

    # Read and execute the SQL file script
    with open("Words.sql", "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()
    print("Database 'dictionary.db' successfully created and populated!")
except Exception as e:
    print(f"An error occurred: {e}")