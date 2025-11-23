from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.rosters.readonly'
]

SERVICE_ACCOUNT_FILE = 'credentials.json'
DELEGATED_ADMIN = 'misha@gedu.demo.cloudreigntech.com'  # your Super Admin email

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

delegated_creds = creds.with_subject(DELEGATED_ADMIN)

service = build('classroom', 'v1', credentials=delegated_creds)

results = service.courses().list(pageSize=10).execute()
courses = results.get('courses', [])

if not courses:
    print("No courses found or insufficient permissions.")
else:
    for course in courses:
        print(f"{course['id']}: {course['name']}")
