import sqlite3

def recordVoteInDB(modName: str, positiveVote: bool, subreddits: str, subWhereVoteRecvd: str):
    con = sqlite3.connect("modrank.db")
    cursor = con.cursor()
    # cursor.execute("CREATE TABLE mods(username TEXT UNIQUE, pos_votes INTEGER, neg_votes INTEGER, subreddits TEXT)")

    subsInWhichModRcvdVotesPrvsly = cursor.execute("""SELECT sub_voted FROM mods WHERE username=? COLLATE NOCASE""", (modName,)).fetchone() # COLLATE NOCASE is to compare case insensitive as maybe in future API may give different case

    if subsInWhichModRcvdVotesPrvsly: # Mod exists in DB

        # 1a start - handling creation of new string which will go in sub_voted column of DB
        newSubFound = True
        newSubsInWhichModRecvdVotesPrvsly = []
        for sub in subsInWhichModRcvdVotesPrvsly[0].split(): # need subscription as it is tuple otherwise, grabbing string from inside with subscription
            oldSubName, noOfVotes = sub.split('~^~')
            if oldSubName.lower() == subWhereVoteRecvd.lower():
                noOfVotes = int(noOfVotes) +1
                newSubFound = False
            newSubsInWhichModRecvdVotesPrvsly.append(f"{oldSubName}~^~{noOfVotes}")
        if newSubFound:
            newSubsInWhichModRecvdVotesPrvsly.append(f"{subWhereVoteRecvd}~^~1")

        subsVoteCountDict = {}
        for sub in newSubsInWhichModRecvdVotesPrvsly:
            oldSubName, noOfVotes = sub.split('~^~')
            subsVoteCountDict[oldSubName] = int(noOfVotes)
        newSubsInWhichModRecvdVotesPrvslySorted = {k: v for k, v in sorted(subsVoteCountDict.items(), key=lambda item: item[1], reverse=True)}
        newSubsInWhichModRecvdVotesPrvslyList = []
        for oldSubName, noOfVotes in newSubsInWhichModRecvdVotesPrvslySorted.items():
            newSubsInWhichModRecvdVotesPrvslyList.append(f"{oldSubName}~^~{noOfVotes}")
        newSubsInWhichModRecvdVotesPrvslyString = ' '.join(newSubsInWhichModRecvdVotesPrvslyList)
        # 1a end
        
        if positiveVote:
            cursor.execute("""
            INSERT INTO mods VALUES (?, 1, 0, ?, ?) 
            ON CONFLICT(username) DO UPDATE SET pos_votes=pos_votes+1, subreddits=?, sub_voted=?
            """, (modName, subreddits, newSubsInWhichModRecvdVotesPrvslyString, subreddits, newSubsInWhichModRecvdVotesPrvslyString)) # use this ? syntax to avoid sql injection lel
            print('inserted positive vote in old mod')
        else:
            cursor.execute("""
            INSERT INTO mods VALUES (?, 0, 1, ?, ?) 
            ON CONFLICT(username) DO UPDATE SET neg_votes=neg_votes+1, subreddits=?, sub_voted=?
            """, (modName, subreddits, newSubsInWhichModRecvdVotesPrvslyString, subreddits, newSubsInWhichModRecvdVotesPrvslyString))
            print('inserted negative vote in old mod')
    else: # New Mod insertion in DB
        subWhereVoteRecvd += "~^~1"
        if positiveVote:
            cursor.execute("""INSERT INTO mods VALUES (?, 1, 0, ?, ?)""", (modName, subreddits, subWhereVoteRecvd)) # use this ? syntax to avoid sql injection
            print("inserted postive vote in new mod")
            
        else:
            print("inserted negative vote in new mod")
            cursor.execute("""INSERT INTO mods VALUES (?, 0, 1, ?, ?)""", (modName, subreddits, subWhereVoteRecvd))

    con.commit()
    # print(cursor.execute("SELECT * FROM mods where username='pintuk'").fetchall())
    con.close()

# useful sqlite/CLI commands
# .open modrank.db (to connect to file, NO SEMICOLON AT END)
# .schema mods (to show table desciption)
# UPDATE mods SET sub_voted='yolo' where username='golo' (to update a row)


# 3 paths to test after adding sub_voted: new mod, old mod new sub, old mod old sub