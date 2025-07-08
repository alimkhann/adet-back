# Support System Backend

This module implements a comprehensive support system for the Adet app, including support requests, bug reports, and admin management.

## Features

### Support Requests
- Users can submit support requests with categories (general, technical, billing, etc.)
- System automatically captures device and app information
- Email notifications sent to users and admins
- Admin can update status, assign tickets, and respond

### Bug Reports
- Users can report bugs with severity levels and detailed information
- Automatic GitHub issue creation for bug reports
- System info collection for debugging
- Admin management with status tracking

### Admin Features
- View all support requests and bug reports
- Update ticket status and assign to team members
- Add internal notes and responses
- View support statistics and analytics

## Database Schema

### SupportRequest
- `id`: Primary key
- `user_id`: Foreign key to users table
- `category`: Support category (general, technical, etc.)
- `subject`: Brief description
- `message`: Detailed description
- `status`: Current status (open, in_progress, resolved, closed)
- `priority`: Priority level (low, medium, high, critical)
- `system_info`: JSON field with device/app information
- `created_at`, `updated_at`, `resolved_at`: Timestamps
- `assigned_to`: Admin assigned to the ticket
- `admin_notes`: Internal admin notes

### BugReport
- `id`: Primary key
- `user_id`: Foreign key to users table
- `category`: Bug category (ui, performance, crash, etc.)
- `severity`: Severity level (low, medium, high, critical)
- `title`: Bug title
- `description`: Detailed description
- `steps_to_reproduce`: Steps to reproduce the bug
- `expected_behavior`: What should happen
- `actual_behavior`: What actually happens
- `status`: Current status
- `system_info`: JSON field with device/app information
- `include_screenshots`: Whether user wants to include screenshots
- `github_issue_url`: Link to GitHub issue (if created)

### SupportResponse
- `id`: Primary key
- `support_request_id`: Foreign key to support request (optional)
- `bug_report_id`: Foreign key to bug report (optional)
- `responder_id`: Foreign key to users table
- `message`: Response message
- `is_internal`: Whether this is an internal note
- `created_at`: Timestamp

## API Endpoints

### Support Requests
- `POST /api/v1/support/request` - Create support request
- `GET /api/v1/support/history` - Get user's support history
- `GET /api/v1/support/request/{request_id}` - Get specific request
- `PUT /api/v1/support/request/{request_id}` - Update request (admin)
- `POST /api/v1/support/request/{request_id}/respond` - Add response

### Bug Reports
- `POST /api/v1/support/bug-report` - Create bug report
- `GET /api/v1/support/bug-reports` - Get user's bug history
- `GET /api/v1/support/bug-report/{report_id}` - Get specific report
- `PUT /api/v1/support/bug-report/{report_id}` - Update report (admin)
- `POST /api/v1/support/bug-report/{report_id}/respond` - Add response

### Admin Endpoints
- `GET /api/v1/support/admin/requests` - Get all support requests
- `GET /api/v1/support/admin/bug-reports` - Get all bug reports
- `GET /api/v1/support/admin/statistics` - Get support statistics

## Configuration

### Environment Variables

#### Email Configuration
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=support@adet.app
SUPPORT_EMAIL=support@adet.app
ADMIN_EMAIL=admin@adet.app
ADMIN_EMAILS=admin@adet.app,admin2@adet.app
```

#### GitHub Integration
```bash
GITHUB_TOKEN=your-github-personal-access-token
GITHUB_OWNER=adet-app
GITHUB_REPO=adet-app
```

## Services

### SupportService
Main service for handling support operations:
- Create and manage support requests
- Create and manage bug reports
- Handle responses and updates
- Provide admin functions

### EmailService
Handles email notifications:
- Support request confirmations
- Bug report confirmations
- Admin notifications
- Status update notifications

### GitHubService
Integrates with GitHub for bug reports:
- Automatically create GitHub issues
- Update issue status
- Link bug reports to GitHub issues

## Admin Access

Admin access is controlled by the `ADMIN_EMAILS` environment variable. Users with emails listed in this variable have access to admin endpoints.

## Database Migration

Run the migration to create the support tables:

```bash
alembic upgrade head
```

## Usage Examples

### Creating a Support Request
```python
from support.models import SupportRequestCreate, SystemInfo

request_data = SupportRequestCreate(
    category="technical",
    subject="App crashes on startup",
    message="The app crashes immediately when I open it",
    system_info=SystemInfo(
        app_version="1.0.0",
        build_number="1",
        ios_version="17.0",
        device_model="iPhone 15",
        device_name="My iPhone",
        language="en",
        timezone="America/New_York",
        timestamp=datetime.now()
    )
)

service = SupportService(db)
support_request = service.create_support_request(user_id, request_data)
```

### Creating a Bug Report
```python
from support.models import BugReportCreate

bug_data = BugReportCreate(
    category="crash",
    severity="high",
    title="App crashes when submitting proof",
    description="The app crashes every time I try to submit a photo proof",
    steps_to_reproduce="1. Open app\n2. Complete a habit task\n3. Try to submit photo proof\n4. App crashes",
    expected_behavior="Photo should be uploaded successfully",
    actual_behavior="App crashes to home screen",
    include_screenshots=True
)

service = SupportService(db)
bug_report = service.create_bug_report(user_id, bug_data)
```

## Security Considerations

1. **Input Validation**: All user inputs are validated using Pydantic models
2. **Access Control**: Admin endpoints are protected by middleware
3. **Rate Limiting**: Consider implementing rate limiting for public endpoints
4. **Data Privacy**: System info is stored but can be anonymized for public reports
5. **Audit Logging**: All admin actions are logged

## Future Enhancements

1. **Knowledge Base**: Create FAQ from resolved tickets
2. **Chat Support**: Integrate live chat for urgent issues
3. **Video Support**: Allow screen recording for bug reports
4. **Automated Responses**: Use AI to suggest responses
5. **Integration**: Connect with external support tools (Zendesk, Intercom)
6. **Analytics**: Advanced reporting and analytics dashboard

This module implements a comprehensive support system for the Adet app, including support requests, bug reports, and admin management.

## Features

### Support Requests
- Users can submit support requests with categories (general, technical, billing, etc.)
- System automatically captures device and app information
- Email notifications sent to users and admins
- Admin can update status, assign tickets, and respond

### Bug Reports
- Users can report bugs with severity levels and detailed information
- Automatic GitHub issue creation for bug reports
- System info collection for debugging
- Admin management with status tracking

### Admin Features
- View all support requests and bug reports
- Update ticket status and assign to team members
- Add internal notes and responses
- View support statistics and analytics

## Database Schema

### SupportRequest
- `id`: Primary key
- `user_id`: Foreign key to users table
- `category`: Support category (general, technical, etc.)
- `subject`: Brief description
- `message`: Detailed description
- `status`: Current status (open, in_progress, resolved, closed)
- `priority`: Priority level (low, medium, high, critical)
- `system_info`: JSON field with device/app information
- `created_at`, `updated_at`, `resolved_at`: Timestamps
- `assigned_to`: Admin assigned to the ticket
- `admin_notes`: Internal admin notes

### BugReport
- `id`: Primary key
- `user_id`: Foreign key to users table
- `category`: Bug category (ui, performance, crash, etc.)
- `severity`: Severity level (low, medium, high, critical)
- `title`: Bug title
- `description`: Detailed description
- `steps_to_reproduce`: Steps to reproduce the bug
- `expected_behavior`: What should happen
- `actual_behavior`: What actually happens
- `status`: Current status
- `system_info`: JSON field with device/app information
- `include_screenshots`: Whether user wants to include screenshots
- `github_issue_url`: Link to GitHub issue (if created)

### SupportResponse
- `id`: Primary key
- `support_request_id`: Foreign key to support request (optional)
- `bug_report_id`: Foreign key to bug report (optional)
- `responder_id`: Foreign key to users table
- `message`: Response message
- `is_internal`: Whether this is an internal note
- `created_at`: Timestamp

## API Endpoints

### Support Requests
- `POST /api/v1/support/request` - Create support request
- `GET /api/v1/support/history` - Get user's support history
- `GET /api/v1/support/request/{request_id}` - Get specific request
- `PUT /api/v1/support/request/{request_id}` - Update request (admin)
- `POST /api/v1/support/request/{request_id}/respond` - Add response

### Bug Reports
- `POST /api/v1/support/bug-report` - Create bug report
- `GET /api/v1/support/bug-reports` - Get user's bug history
- `GET /api/v1/support/bug-report/{report_id}` - Get specific report
- `PUT /api/v1/support/bug-report/{report_id}` - Update report (admin)
- `POST /api/v1/support/bug-report/{report_id}/respond` - Add response

### Admin Endpoints
- `GET /api/v1/support/admin/requests` - Get all support requests
- `GET /api/v1/support/admin/bug-reports` - Get all bug reports
- `GET /api/v1/support/admin/statistics` - Get support statistics

## Configuration

### Environment Variables

#### Email Configuration
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=support@adet.app
SUPPORT_EMAIL=support@adet.app
ADMIN_EMAIL=admin@adet.app
ADMIN_EMAILS=admin@adet.app,admin2@adet.app
```

#### GitHub Integration
```bash
GITHUB_TOKEN=your-github-personal-access-token
GITHUB_OWNER=adet-app
GITHUB_REPO=adet-app
```

## Services

### SupportService
Main service for handling support operations:
- Create and manage support requests
- Create and manage bug reports
- Handle responses and updates
- Provide admin functions

### EmailService
Handles email notifications:
- Support request confirmations
- Bug report confirmations
- Admin notifications
- Status update notifications

### GitHubService
Integrates with GitHub for bug reports:
- Automatically create GitHub issues
- Update issue status
- Link bug reports to GitHub issues

## Admin Access

Admin access is controlled by the `ADMIN_EMAILS` environment variable. Users with emails listed in this variable have access to admin endpoints.

## Database Migration

Run the migration to create the support tables:

```bash
alembic upgrade head
```

## Usage Examples

### Creating a Support Request
```python
from support.models import SupportRequestCreate, SystemInfo

request_data = SupportRequestCreate(
    category="technical",
    subject="App crashes on startup",
    message="The app crashes immediately when I open it",
    system_info=SystemInfo(
        app_version="1.0.0",
        build_number="1",
        ios_version="17.0",
        device_model="iPhone 15",
        device_name="My iPhone",
        language="en",
        timezone="America/New_York",
        timestamp=datetime.now()
    )
)

service = SupportService(db)
support_request = service.create_support_request(user_id, request_data)
```

### Creating a Bug Report
```python
from support.models import BugReportCreate

bug_data = BugReportCreate(
    category="crash",
    severity="high",
    title="App crashes when submitting proof",
    description="The app crashes every time I try to submit a photo proof",
    steps_to_reproduce="1. Open app\n2. Complete a habit task\n3. Try to submit photo proof\n4. App crashes",
    expected_behavior="Photo should be uploaded successfully",
    actual_behavior="App crashes to home screen",
    include_screenshots=True
)

service = SupportService(db)
bug_report = service.create_bug_report(user_id, bug_data)
```

## Security Considerations

1. **Input Validation**: All user inputs are validated using Pydantic models
2. **Access Control**: Admin endpoints are protected by middleware
3. **Rate Limiting**: Consider implementing rate limiting for public endpoints
4. **Data Privacy**: System info is stored but can be anonymized for public reports
5. **Audit Logging**: All admin actions are logged

## Future Enhancements

1. **Knowledge Base**: Create FAQ from resolved tickets
2. **Chat Support**: Integrate live chat for urgent issues
3. **Video Support**: Allow screen recording for bug reports
4. **Automated Responses**: Use AI to suggest responses
5. **Integration**: Connect with external support tools (Zendesk, Intercom)
6. **Analytics**: Advanced reporting and analytics dashboard

