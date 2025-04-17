from typing import Dict, List, Optional
from datetime import datetime
from .session import CFSession

class ContestAPI:
    def __init__(self, session: CFSession):
        self.session = session

    def get_contests(self, type: str = 'upcoming', limit: int = 5) -> Dict:
        """Fetch contest information"""
        try:
            response = self.session.call_api("contest.list")
            if response.get("status") != "OK":
                return {"status": "FAILED", "comment": response.get("comment", "Unknown error")}
                
            contests = response.get("result", [])
            
            # Filter contests based on type
            current_time = int(time.time())
            filtered_contests = []
            
            for contest in contests:
                if type == 'upcoming' and contest.get('phase') == 'BEFORE':
                    filtered_contests.append(contest)
                elif type == 'running' and contest.get('phase') == 'CODING':
                    filtered_contests.append(contest)
                elif type == 'past' and contest.get('phase') == 'FINISHED':
                    filtered_contests.append(contest)
            
            # Sort and limit
            if type == 'upcoming':
                filtered_contests.sort(key=lambda c: c.get('startTimeSeconds', 0))
            else:
                filtered_contests.sort(key=lambda c: c.get('startTimeSeconds', 0), reverse=True)
            
            return {"status": "OK", "result": filtered_contests[:limit]}
            
        except Exception as e:
            return {"status": "FAILED", "comment": str(e)}

    def get_contest_problems(self, contest_id: int) -> Dict:
        """Fetch problems for a specific contest"""
        try:
            response = self.session.call_api("contest.standings", {
                "contestId": contest_id,
                "from": 1,
                "count": 1
            })
            
            if response.get("status") != "OK":
                return {"status": "FAILED", "comment": response.get("comment", "Unknown error")}
                
            problems = response.get("result", {}).get("problems", [])
            return {"status": "OK", "result": problems}
            
        except Exception as e:
            return {"status": "FAILED", "comment": str(e)}

    def get_contest_status(self, contest_id: int) -> Dict:
        """Get contest status and submissions"""
        try:
            response = self.session.call_api("contest.status", {
                "contestId": contest_id
            })
            
            if response.get("status") != "OK":
                return {"status": "FAILED", "comment": response.get("comment", "Unknown error")}
                
            submissions = response.get("result", [])
            return {"status": "OK", "result": submissions}
            
        except Exception as e:
            return {"status": "FAILED", "comment": str(e)} 