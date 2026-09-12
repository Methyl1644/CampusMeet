# CampusMate Tag Governance and Resource Permissions Design

## Goal

Build a controlled campus activity vocabulary and allow verified users to receive narrowly scoped permissions for one topic or one recruitment post.

## Tag principles

- A Tag represents a reusable concept such as activity type, skill, recruitment role, audience, or event level.
- A competition name belongs to the topic catalog. A new edition creates a topic, not a new Tag.
- Canonical names and aliases are distinct. Ambiguous phrases are not global aliases unless an operator approves them.
- AI may select active candidate Tags and propose unknown concepts. It cannot publish, rename, merge, or activate a Tag.
- Unknown concepts enter a review queue with the source text, proposed category, similar Tags, reason, and occurrence count.
- Operators decide whether a proposal becomes a canonical Tag, an alias of an existing Tag, remains searchable free text, or is rejected.

## Initial taxonomy

The catalog covers reusable activity, skill, recruitment role, event level, and audience concepts. Time, place, member count, status, organization, and exact event name remain structured fields rather than Tags.

## Tag proposal states

`pending -> approved | merged | rejected`

- `approved`: create a new canonical Tag.
- `merged`: add the proposal term as an alias of an existing Tag.
- `rejected`: record the decision and prevent repeated automatic proposals for the same normalized term.

All decisions store the reviewer, review time, and reason. Repeated observations update one proposal rather than creating duplicates.

## Permission model

Existing platform and organization roles remain in place: platform operator; organization owner, publisher, and member; verified campus user.

Resource roles add limited authority:

- topic coordinator: moderate recruitment posts linked to one topic;
- topic editor: coordinator permissions plus editing the topic information;
- topic manager: editor permissions plus inviting or revoking topic collaborators;
- post application manager: process applications and recruitment state for one post;
- post editor: application manager permissions plus editing the post.

An organization publisher may create an organization topic. Editing another publisher's topic requires organization ownership or an explicit resource role.

## Permission lifecycle

Resource permission records use `pending`, `active`, and `revoked` states. The invited user must accept before a grant becomes active. Grants may expire and should normally expire 30 days after the activity ends.

Platform operators may manage every resource. Organization owners may manage topics belonging to their organization. A resource manager may manage collaborators only for that resource. Post authors retain control of their own posts.

Every invitation, acceptance, revocation, edit, moderation action, and review decision is written to the audit log. The backend checks permission on every operation.

## AI boundary

The backend retrieves relevant active Tags and sends only those candidates to Coze. Coze returns structured Tag IDs and may return separate unknown concept proposals. The backend validates the response schema, discards IDs outside the candidate set, and stores valid proposals as pending.

Authentication evidence, passwords, private contact details, and organization verification evidence are never sent to Coze. AI output cannot grant roles or approve official identity.

## Compatibility

- Existing active Tags and aliases remain valid.
- New tables are additive so the current public deployment can upgrade without deleting user data.
- The legacy JSON `posts.tags` field remains readable while `post_tags` is the controlled source for new writes.

## Acceptance criteria

- Existing aliases resolve to canonical Tag IDs and ambiguous terms do not silently map to a single activity.
- Unknown concepts create or increment one pending proposal and never become active automatically.
- Only operators can approve, merge, or reject Tag proposals.
- A verified ordinary user can accept a grant for exactly one topic or post without gaining broader authority.
- Topic coordinators cannot edit official information; topic editors can; topic managers can manage collaborators.
- Post application managers cannot edit post content; post editors can.
- Revoked and expired permissions stop working immediately.
- Permission and Tag review actions are auditable.

