import psycopg
conn = psycopg.connect('host=localhost port=5432 dbname=datawarehouse user=bdii_user password=admin123')
print('Conectado!')
conn.close()