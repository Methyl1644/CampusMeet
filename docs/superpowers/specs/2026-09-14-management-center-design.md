# Management Center Design

## Goal

Add one permission-aware management center at `/management` for platform operators and verified organization owners. The center must expose existing role, organization, and collaborator workflows without changing ordinary member publishing or team participation.

## Information Architecture

The user menu shows `管理中心` only after `/api/me/permissions` reports at least one management capability. The page uses a compact left navigation and a full-width work area with four possible sections:

- `平台角色`: list platform grants; senior operators can invite, suspend, and revoke roles.
- `组织审核`: list pending organization applications; operators can inspect and approve or reject them.
- `组织成员`: list organizations owned by the current user, invite publishers or members, revoke memberships, and transfer ownership.
- `活动负责人`: enter an activity ID, list collaborators, and invite or revoke coordinator, editor, or manager grants.

Only authorized sections are shown. Direct visits by users with no management capability render a clear access-denied state instead of exposing empty controls.

## Permission Model

The frontend uses permissions only for navigation and presentation. Every mutation remains protected by the existing backend authorization rules.

- `operator` and `senior_operator` can view platform roles and organization applications.
- Only `senior_operator` can mutate platform roles.
- Active organization `owner` memberships enable organization member management.
- Topic owners, platform operators, and topic `manager` collaborators can manage topic collaborators.
- Organization `publisher` and `member` roles do not receive organization administration controls.

## Data Flow

`management.ts` is the single frontend API module for permission, platform-role, organization, and collaborator requests. The page loads permissions first, derives visible sections, then lazily loads the selected section. Mutations refresh only their own section and report backend messages through the existing toast system.

The backend adds a current-user organization summary endpoint because the existing identity projection is not sufficient to populate the organization selector. Existing role, review, invitation, ownership-transfer, and collaborator endpoints remain unchanged.

## Interaction And Visual Style

The page follows the current CampusMate/Meetup-inspired system: white background, restrained green accents, thin borders, compact rows, 8px-or-less radii, and Lucide icons. Desktop uses a 220px navigation rail; mobile uses a horizontally scrollable tab row. Destructive actions require an inline confirmation step. Forms use labels, selects, and explicit submit buttons rather than decorative cards.

## States And Errors

Every section supports loading, empty, success, and error states. Backend error detail is shown verbatim through `getApiErrorMessage`. Pending invitations and expired grants are labeled. A failed mutation leaves the form data intact.

## Testing

Tests cover permission-derived menu visibility, route access, section visibility, platform invitations, organization review, organization-member invitations, and topic collaborator invitations. Backend tests cover the current-user organization summary endpoint. Production TypeScript and Vite builds must pass.

