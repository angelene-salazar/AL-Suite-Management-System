from views import LoginWindow
import database
import sys

def main():
    database.init_db()
    app = LoginWindow()
    app.mainloop()

if __name__ == "__main__":
    main()

