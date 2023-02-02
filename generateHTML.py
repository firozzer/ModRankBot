import sqlite3, subprocess, os
from bs4 import BeautifulSoup

def generateHTMLAndPushToGithub(modNames:list):
    baseHTML = """
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Testing</title>
    <link rel="stylesheet" href="index.css">
    </head>
    <body>
    <div id="mainContent">
        <table id="rankingsTable">
        <tr>
            <th>Mod Name</th>
            <th>+ve Votes</th>
            <th>-ve Votes</th>
        </tr>
        </table>
    </div>
    </body>
    <footer>
    <script src="index.js"></script>
    </footer>
    </html>
    """

    soup = BeautifulSoup(baseHTML)
    tableElem = soup.find('table', {'id': 'rankingsTable'})
    con = sqlite3.connect("modrank.db")
    cursor = con.cursor()
    rowsFromSQLite = cursor.execute("SELECT * FROM mods ORDER BY pos_votes DESC").fetchall()
    for row in rowsFromSQLite:
        tableElem.append(BeautifulSoup(f'<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td>', 'html.parser'))

    os.chdir('frontend/')
    with open(r'index.html', "w", encoding="utf-8") as file:
        file.write(str(soup))
    
    input("shall i run git?")
    # commit to local git
    subprocess.run(f"""git add . ; git commit -m "{' '.join(modNames)} new vote/s added" ; git push origin main """, shell=True)


generateHTMLAndPushToGithub(['testuser1', 'testuser2'])