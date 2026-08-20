import sqlite3
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Execute DML ou DQL no app.db (SQLite)')
    parser.add_argument('query', type=str, help='Comando SQL a ser executado (ex: "UPDATE users SET role = \'gestor\'")')
    parser.add_argument('--db', type=str, default='app.db', help='Caminho do banco de dados (padrão: app.db)')

    args = parser.parse_args()
    query = args.query.strip()
    
    try:
        conn = sqlite3.connect(args.db)
        cursor = conn.cursor()
        
        # Ativa suporte a chaves estrangeiras por segurança
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        cursor.execute(query)
        
        # Se for um comando de leitura (SELECT), exibe o resultado
        if query.upper().startswith("SELECT"):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            print(f"✅ {len(rows)} linhas retornadas:")
            print(" | ".join(columns))
            print("-" * (len(" | ".join(columns))))
            
            for row in rows:
                print(" | ".join(str(cell) for cell in row))
        else:
            # Se for DML (INSERT, UPDATE, DELETE), faz o commit
            conn.commit()
            print(f"✅ Comando executado com sucesso! Linhas afetadas: {cursor.rowcount}")
            
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao executar SQL: {e}")

if __name__ == "__main__":
    main()
