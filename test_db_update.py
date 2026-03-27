
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def test_update():
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'junji'),
            password=os.getenv('DB_PASSWORD', 'Tijunji2017'),
            database=os.getenv('DB_NAME', 'inventariofinal'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cur:
            # 1. Get an equipment
            cur.execute("SELECT idEquipo, ObservacionEquipo FROM equipo LIMIT 1")
            equipo = cur.fetchone()
            if not equipo:
                print("No equipment found")
                return
            
            orig_id = equipo['idEquipo']
            orig_obs = equipo['ObservacionEquipo'] or ""
            new_obs = f"Test override {os.urandom(4).hex()}"
            
            print(f"Original ID: {orig_id}, Obs: {orig_obs}")
            print(f"Updating to: {new_obs}")
            
            # 2. Update it
            cur.execute("UPDATE equipo SET ObservacionEquipo = %s WHERE idEquipo = %s", (new_obs, orig_id))
            conn.commit()
            
            # 3. Verify
            cur.execute("SELECT ObservacionEquipo FROM equipo WHERE idEquipo = %s", (orig_id,))
            updated = cur.fetchone()
            print(f"Updated Obs: {updated['ObservacionEquipo']}")
            
            if updated['ObservacionEquipo'] == new_obs:
                print("SUCCESS: Update worked in DB")
            else:
                print("FAILURE: Update did not persist")
                
            # 4. Restore
            cur.execute("UPDATE equipo SET ObservacionEquipo = %s WHERE idEquipo = %s", (orig_obs, orig_id))
            conn.commit()
            print("Restored original observation")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    test_update()
