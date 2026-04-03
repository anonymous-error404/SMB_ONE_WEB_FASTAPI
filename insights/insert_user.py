import psycopg2
import hashlib

def seed_user():
    params = {
        "host": "localhost",
        "database": "smb_one_db",
        "user": "postgres",
        "password": "Rajnikant@1",
        "port": 5432
    }
    conn = psycopg2.connect(**params)
    cursor = conn.cursor()
    
    hashed_password = hashlib.sha256(b"password").hexdigest()
    hashed_answer = hashlib.sha256(b"answer").hexdigest()
    
    try:
        cursor.execute("INSERT INTO users (name, email, password, security_question, security_answer) VALUES (%s, %s, %s, %s, %s)", 
                       ("Rakesh Singh", "rakesh@gmail.com", hashed_password, "Question?", hashed_answer))
        conn.commit()
        print("✅ Added Rakesh Singh user!")
    except psycopg2.IntegrityError:
        print("User already exists.")
    
    conn.close()

if __name__ == "__main__":
    seed_user()
