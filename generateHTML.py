import sqlite3, subprocess, os
from bs4 import BeautifulSoup

def generateHTMLAndPushToGithub(modNames:list):
    baseHTML = """
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="X-UA-Compatible" content="IE=edge">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reddit Mod Ranks</title>
            <link rel="stylesheet" href="index.css">
        </head>
        <body>
            <div id="mainContent">
                <table id="rankingsTable">
                    <tr>
                        <th>Mod Name</th>
                        <th>+ve Votes</th>
                        <th>-ve Votes</th>
                        <th>Score*</th>
                    </tr>
                </table>
                <div id="statsBelowTable"></div>
            </div>
        </body>
        <footer>
            <script src="index.js"></script>
        </footer>
    </html>
    """

    soup = BeautifulSoup(baseHTML)
    tableElem = soup.find('table', {'id': 'rankingsTable'})
    statsBelowTableElem = soup.find('div', {'id': 'statsBelowTable'})
    con = sqlite3.connect("modrank.db")
    cursor = con.cursor()
    rowsFromSQLite = cursor.execute("SELECT username, pos_votes, neg_votes FROM mods ORDER BY (pos_votes-neg_votes) DESC").fetchall() # you'll get username:Str, posVotes:Int, negVotes:Int & subsModded:Str. Last is delimited by space.
    totalNoOfModsInDB = 0
    totalVotesInDB = 0
    for row in rowsFromSQLite:
        tableElem.append(BeautifulSoup(f'<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[1]-row[2]}</td>', 'html.parser'))
        totalNoOfModsInDB += 1; totalVotesInDB += row[1] + row[2]
    statsBelowTableElem.append(BeautifulSoup(f"<p>Total Mods: {totalNoOfModsInDB} | Total Votes: {totalVotesInDB} | *Score = Pos - Neg Votes</p>", 'html.parser'))

    os.chdir('frontend/')
    with open(r'index.html', "w", encoding="utf-8") as file:
        file.write(str(soup))
    
    # commit to local git & push to Github, from where Netlify will pickup autoly
    subprocess.run(f"""git add . ; git commit -m "{' '.join(modNames)} new vote/s added" ; git push origin main """, shell=True)
    # to bypass creds request everytime on push, i ran 'git config credential.helper store' from Stackoverlfow. This method is BAD because it stores pw in plaintext in Git.
    