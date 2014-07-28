from opencivicdata.models import (Jurisdiction, Organization, Person,
                                  Bill, VoteEvent, Event)
from .helpers import PublicListEndpoint, PublicDetailEndpoint, get_field_list
from collections import defaultdict
import pytz


def dout(obj):
    """
    Helper function to ensure that we're always printing internal
    datetime objects in a fully qualified UTC timezone. This will
    let 'None' values pass through untouched.
    """
    if obj is None:
        return
    return pytz.UTC.localize(obj).isoformat()


class BlacklistDefaultDict(defaultdict):
    def __init__(self, *args, blacklist=None, **kwargs):
        self.blacklist = [] if blacklist is None else blacklist
        super(BlacklistDefaultDict, self).__init__(*args, **kwargs)

    def __getitem__(self, key, *args, **kwargs):
        if key in self.blacklist:
            raise KeyError("No such key: %s" % (key))

        return super(BlacklistDefaultDict, self).__getitem__(
            key, *args, **kwargs
        )

    def items(self, *args, **kwargs):
        for k, v in defaultdict.items(self, *args, **kwargs):
            if k in self.blacklist:
                continue
            yield (k, v)

    def __str__(self, *args, **kwargs):
        return "BlacklistDefaultDict({})".format(
            super(BlacklistDefaultDict, self).__str__(*args, **kwargs)
        )

DIVISION_SERIALIZE = defaultdict(dict)
SOURCES_SERIALIZE = {"note": {}, "url": {},}

JURISDICTION_SERIALIZE = defaultdict(dict, [
    ("extras", lambda x: x.extras),
    ("feature_flags", lambda x: x.feature_flags),
    ("division", DIVISION_SERIALIZE),
])

LEGISLATIVE_SESSION_SERIALIZE = defaultdict(dict, [
    ('jurisdiction', JURISDICTION_SERIALIZE),
])


ORGANIZATION_SERIALIZE = defaultdict(dict, [
    ("jurisdiction", JURISDICTION_SERIALIZE),
    ("sources", SOURCES_SERIALIZE),
])
ORGANIZATION_SERIALIZE['parent'] = ORGANIZATION_SERIALIZE
ORGANIZATION_SERIALIZE['children'] = ORGANIZATION_SERIALIZE

ORGANIZATION_SERIALIZE['identifiers'] = {
    # Don't leak 'id'
    "identifier": {},
    # Don't allow recuse into our own org.
    "scheme": {},
}

PERSON_SERIALIZE = defaultdict(dict, [
    ("sources", SOURCES_SERIALIZE),
])

POST_SERIALIZE = defaultdict(dict, [
    ("organization", ORGANIZATION_SERIALIZE),
    ("division", DIVISION_SERIALIZE),
])

ORGANIZATION_SERIALIZE['posts'] = POST_SERIALIZE

MEMBERSHIP_SERIALIZE = {
    # Explicit to avoid letting `id' leak out.
    "start_date": {},
    "end_date": {},
    "role": {},
    "label": {},
    "organization": ORGANIZATION_SERIALIZE,
    "person": PERSON_SERIALIZE,
    "post": POST_SERIALIZE,
    "on_behalf_of": ORGANIZATION_SERIALIZE,
}

ORGANIZATION_SERIALIZE['memberships'] = BlacklistDefaultDict(
    dict,
    MEMBERSHIP_SERIALIZE.items(),
    blacklist=['organization']
)
PERSON_SERIALIZE['memberships'] = MEMBERSHIP_SERIALIZE
POST_SERIALIZE['memberships'] = MEMBERSHIP_SERIALIZE

LINK_BASE = defaultdict(dict, [
    ('links', {
        'media_type': {},
        'url': {},
    }),
])

BILL_SERIALIZE = defaultdict(dict, [
    ('legislative_session', LEGISLATIVE_SESSION_SERIALIZE),
    ('from_organization', ORGANIZATION_SERIALIZE),
    ('classification', lambda x: x.classification),
    ('subject', lambda x: x.classification),
    ('actions', {
        'organization': ORGANIZATION_SERIALIZE,
        'classification': lambda x: x.classification,
    }),
    ('documents', {
        "note": {}, "date": {}, "links": LINK_BASE,
    }),
    ('versions', {
        "note": {}, "date": {}, "links": LINK_BASE,
    }),
    ('abstracts', defaultdict(dict)),
    ('other_titles', defaultdict(dict)),
    ('other_identifiers', defaultdict(dict)),
    ('sponsorships', {"primary": {}, "classification": {}}),
])

VOTE_SERIALIZE = defaultdict(dict, [
])

EVENT_AGENDA_ITEM = defaultdict(dict, [
    ('subjects', lambda x: x.subjects),
    ('related_entities', defaultdict(dict)),
])

EVENT_SERIALIZE = defaultdict(dict, [
    ('start_time', lambda x: dout(x.start_time)),
    ('end_time', lambda x: dout(x.end_time)),
    ('jurisdiction', JURISDICTION_SERIALIZE),
    ('agenda', EVENT_AGENDA_ITEM),
    ('extras', lambda x: x.extras),
])


class JurisdictionList(PublicListEndpoint):
    model = Jurisdiction
    serialize_config = JURISDICTION_SERIALIZE
    default_fields = ['id', 'name', 'url', 'classification', 'feature_flags',
                      'division.id', 'division.display_name']

    def adjust_filters(self, params):
        if 'name' in params:
            params['name__icontains'] = params.pop('name')
        return params


class JurisdictionDetail(PublicDetailEndpoint):
    model = Jurisdiction
    serialize_config = JURISDICTION_SERIALIZE
    default_fields = get_field_list(model, without=[
        'event_locations',
        'events',
        'organizations',
        'division',
    ]) + [
        'division.id', 'division.display_name'
    ]


class OrganizationList(PublicListEndpoint):
    model = Organization
    serialize_config = ORGANIZATION_SERIALIZE
    default_fields = ['id', 'name', 'image', 'classification',
                      'jurisdiction.id', 'parent.id', 'parent.name',
                      'memberships.person.id', 'memberships.person.name',
                      'memberships.post.id', 'memberships.post.label',
                      'memberships.post.role',]


class OrganizationDetail(PublicDetailEndpoint):
    model = Organization
    serialize_config = ORGANIZATION_SERIALIZE
    default_fields = get_field_list(model, without=[
        'memberships_on_behalf_of',
        'billactionrelatedentity',
        'eventrelatedentity',
        'eventparticipant',
        'billsponsorship',
        'memberships',  # Below.
        'parent_id',  # Present as parent.id
        'children',
        'actions',
        'parent',  # Below.
        'posts',
        'bills',
        'votes',
    ]) + [
        'parent.id',
        'parent.name',

        'memberships.start_date',
        'memberships.end_date',
        'memberships.person.id',
        'memberships.person.name',
        'memberships.post.id',

        'children.id',
        'children.name',

        'jurisdiction.id',
        'jurisdiction.name',
        'jurisdiction.division.id',
        'jurisdiction.division.display_name',

        'posts.id',
        'posts.label',
        'posts.role',
    ]



class PeopleList(PublicListEndpoint):
    model = Person
    serialize_config = PERSON_SERIALIZE
    default_fields = [
        'name', 'id', 'sort_name', 'image', 'gender',

        'memberships.organization.id',
        'memberships.organization.name',
        'memberships.organization.classification',
        'memberships.organization.jurisdiction.id',
        'memberships.organization.jurisdiction.name',

        'memberships.post.id',
        'memberships.post.label',
        'memberships.post.role',
    ]


class PersonDetail(PublicDetailEndpoint):
    model = Person
    serialize_config = PERSON_SERIALIZE
    default_fields = get_field_list(model)
    # default_fields = [
    #     'id', 'name', 'sort_name', 'image', 'gender', 'summary',
    #     'national_identity', 'biography', 'birth_date', 'death_date',

    #     'memberships.organization.id',
    #     'memberships.organization.name',
    #     'memberships.organization.classification',

    #     'memberships.organization.jurisdiction.id',
    #     'memberships.organization.jurisdiction.name',

    #     'memberships.organization.jurisdiction.division.id',
    #     'memberships.organization.jurisdiction.division.display_name',

    #     'memberships.post.id',
    #     'memberships.post.label',
    #     'memberships.post.role',
    # ]


class BillList(PublicListEndpoint):
    model = Bill
    serialize_config = BILL_SERIALIZE
    default_fields = [
        'id', 'identifier', 'title', 'classification',

        'from_organization.name',
        'from_organization.id',

        'from_organization.jurisdiction.id',
        'from_organization.jurisdiction.name',
    ]


class BillDetail(PublicDetailEndpoint):
    model = Bill
    serialize_config = BILL_SERIALIZE
    default_fields = get_field_list(model)
    # default_fields = [
    #     'id', 'identifier', 'title', 'classification', 'abstracts',

    #     'other_titles.title',
    #     'other_titles.note',

    #     'from_organization.name',
    #     'from_organization.id',

    #     'from_organization.jurisdiction.id',
    #     'from_organization.jurisdiction.name',

    #     'documents.note',
    #     'documents.date',
    #     'documents.links.url',
    #     'documents.links.media_type',

    #     'versions.note',
    #     'versions.date',
    #     'versions.links.url',
    #     'versions.links.media_type',
    # ]


class VoteList(PublicListEndpoint):
    model = VoteEvent
    serialize_config = VOTE_SERIALIZE
    default_fields = []


class VoteDetail(PublicDetailEndpoint):
    model = VoteEvent
    serialize_config = VOTE_SERIALIZE
    default_fields = get_field_list(model)


class EventList(PublicListEndpoint):
    model = Event
    serialize_config = EVENT_SERIALIZE
    default_fields = [
        'id', 'name', 'description', 'classification', 'start_time',
        'timezone', 'end_time', 'all_day', 'status',

        'agenda.description', 'agenda.order', 'agenda.subjects',
        'agenda.related_entities.note',
        'agenda.related_entities.entity_name',
    ]


class EventDetail(PublicDetailEndpoint):
    model = Event
    serialize_config = EVENT_SERIALIZE
    default_fields = get_field_list(model)
