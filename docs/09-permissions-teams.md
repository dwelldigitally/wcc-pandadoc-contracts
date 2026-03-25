# PandaDoc Permissions & Teams

## Hierarchy

```
Organization
  └── Workspaces (isolated environments)
        └── Users with Roles
```

## Predefined Roles

| Role | Capabilities |
|------|-------------|
| **Account Owner** | Full control including billing and license management |
| **Admin** | Manage users, settings, and all documents in workspace(s) |
| **Manager** | View/edit/delete workflow templates; monitor team progress |
| **Team Member** | Create and send own documents; view (not edit) others' templates; cannot see others' documents unless added as collaborator |
| **Collaborator** | View and comment on shared documents only; cannot create or send |

## Key Features

### Custom Roles (Enterprise)
- Create custom permission sets
- Enable per-workspace

### Cross-Workspace Roles
- A user can have different roles in different workspaces
- Example: Admin in Admissions, Member in Financial Aid

### Template Sharing
- Control who can view, use, and edit templates
- Share across workspaces or keep workspace-specific

### SSO
- Single Sign-On support at Organization level

### User Provisioning
- Available via API for automated user management

## Enrollment Team Setup

| Person | Role | Workspace |
|--------|------|-----------|
| Registrar | Admin | Admissions |
| Enrollment Counselors | Member | Admissions |
| Department Heads | Collaborator | Admissions |
| Financial Aid Staff | Member | Financial Aid |
| IT Admin | Admin | All Workspaces |

**Key rules:**
- Lock down template editing to Admins only
- Use Collaborator roles for review-only access
- Separate workspaces per department
