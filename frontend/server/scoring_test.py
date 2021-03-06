"""Tests for the bob_emploi.frontend.scoring module."""
import collections
import datetime
import json
import numbers
from os import path
import random
import unittest

import mock
import mongomock

from bob_emploi.frontend import scoring
from bob_emploi.frontend import proto
from bob_emploi.frontend.api import geo_pb2
from bob_emploi.frontend.api import job_pb2
from bob_emploi.frontend.api import project_pb2
from bob_emploi.frontend.api import training_pb2
from bob_emploi.frontend.api import user_pb2

_TESTDATA_FOLDER = path.join(path.dirname(__file__), 'testdata')

# TODO: Clean that up.
# pylint: disable=too-many-lines


def _load_json_to_mongo(database, collection):
    """Load a MongoDB collection from a JSON file."""
    with open(path.join(_TESTDATA_FOLDER, collection + '.json')) as json_file:
        json_blob = json.load(json_file)
    database[collection].insert_many(json_blob)


class _Persona(object):
    """A preset user and project.

    Do not modify the proto of a persona in a test unless you have just
    created/cloned it, otherwise your modifications will impact all the future
    use of the personas. As we only load the personas once during the module
    load, please consider them as constants.

    Attributes:
        name: a keyword that references this persona in our tests.
        user_profile: a UserProfile protobuf defining their profile
        project: a Project protobuf defining their main project.
    """

    def __init__(self, name, user_profile, project, features_enabled=None):
        self.name = name
        self.user_profile = user_profile
        self.project = project
        self.features_enabled = features_enabled or user_pb2.Features()

    @classmethod
    def load_set(cls, filename):
        """Load a set of personas from a JSON file."""
        with open(filename) as personas_file:
            personas_json = json.load(personas_file)
        personas = {}
        for name, blob in personas_json.items():
            user_profile = user_pb2.UserProfile()
            assert proto.parse_from_mongo(blob['user'], user_profile)
            features_enabled = user_pb2.Features()
            if 'featuresEnabled' in blob:
                assert proto.parse_from_mongo(blob['featuresEnabled'], features_enabled)
            project = project_pb2.Project()
            assert proto.parse_from_mongo(blob['project'], project)
            assert name not in personas
            personas[name] = cls(
                name, user_profile=user_profile, project=project, features_enabled=features_enabled)
        return personas

    def scoring_project(self, database, now=None):
        """Creates a new scoring.ScoringProject for this persona."""
        return scoring.ScoringProject(
            project=self.project,
            user_profile=self.user_profile,
            features_enabled=self.features_enabled,
            database=database,
            now=now)

    def clone(self):
        """Clone this persona.

        This is useful if you want a slightly modified persona: you clone an
        existing one and then can modify its protobufs without modifying the
        original one.
        """
        name = '%s cloned' % self.name
        user_profile = user_pb2.UserProfile()
        user_profile.CopyFrom(self.user_profile)
        project = project_pb2.Project()
        project.CopyFrom(self.project)
        return _Persona(name=name, user_profile=user_profile, project=project)


_PERSONAS = _Persona.load_set(path.join(_TESTDATA_FOLDER, 'personas.json'))


def ScoringModelTestBase(model_id):  # pylint: disable=invalid-name
    """Creates a base class for unit tests of a scoring model."""

    class _TestCase(unittest.TestCase):

        @classmethod
        def setUpClass(cls):
            super(_TestCase, cls).setUpClass()
            cls.model_id = model_id
            cls.model = scoring.get_scoring_model(model_id)

        def setUp(self):
            super(_TestCase, self).setUp()
            self.database = mongomock.MongoClient().test

        def _score_persona(self, persona=None, name=None):
            if not persona:
                persona = _PERSONAS[name]
            project = persona.scoring_project(self.database)
            return self.model.score(project)

        def _assert_score_for_empty_project(self, expected):
            score = self._score_persona(name='empty')
            self.assertEqual(expected, score)

        def _random_persona(self):
            return _PERSONAS[random.choice(list(_PERSONAS))]

    return _TestCase


class DefaultScoringModelTestCase(ScoringModelTestBase('')):
    """Unit test for the default scoring model."""

    def test_score(self):
        """Test the score function."""
        score = self._score_persona(self._random_persona())

        self.assertLessEqual(score, 3)
        self.assertLessEqual(0, score)


class AdviceEventScoringModelTestCase(ScoringModelTestBase('advice-event')):
    """Unit test for the "Event Advice" scoring model."""

    def setUp(self):
        super(AdviceEventScoringModelTestCase, self).setUp()
        self.persona = self._random_persona().clone()
        self.database.events.insert_many([
            {
                'title': 'AP HEROS CANDIDATS MADIRCOM - BORDEAUX',
                'link': 'https://www.workuper.com/events/ap-heros-candidats-madircom-bordeaux',
                'organiser': 'MADIRCOM',
                'startDate': '2017-08-29',
            },
            {
                'title': 'Le Salon du Travail et de la Mobilité Professionnelle',
                'link': 'https://www.workuper.com/events/le-salon-du-travail-et-de-la-mobilite-'
                        'professionnelle',
                'organiser': 'Altice Media Events',
                'startDate': '2018-01-19',
            },
        ])

    def test_important_application(self):
        """Network is important for the user."""
        self.persona.project.target_job.job_group.rome_id = 'A1234'
        self.persona.project.mobility.city.departement_id = '69'
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'applicationModes': {
                'R4Z92': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        }
                    ],
                }
            },
        })
        score = self._score_persona(self.persona)
        self.assertGreaterEqual(score, 2, msg='Fail for "%s"' % self.persona.name)

    def test_unimportant_application(self):
        """Network is important for the user."""
        self.persona.project.target_job.job_group.rome_id = 'A1234'
        self.persona.project.mobility.city.departement_id = '69'
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'applicationModes': {
                'R4Z92': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        }
                    ],
                }
            },
        })
        score = self._score_persona(self.persona)
        self.assertLessEqual(score, 1, msg='Fail for "%s"' % self.persona.name)


class TrainingAdviceScoringModelTestCase(ScoringModelTestBase('advice-training')):
    """Unit test for the training scoring model."""

    def setUp(self):
        """Setting up the persona for a test."""
        super(TrainingAdviceScoringModelTestCase, self).setUp()
        self.persona = self._random_persona().clone()
        self._many_trainings = [
            training_pb2.Training(),
            training_pb2.Training(),
            training_pb2.Training(),
        ]

    @mock.patch(scoring.carif.__name__ + '.get_trainings')
    def test_low_advice_for_new_de(self, mock_carif_get_trainings):
        """The user just started searching for a job."""
        mock_carif_get_trainings.return_value = self._many_trainings
        self.persona.project.mobility.city.departement_id = '35'
        self.persona.project.target_job.job_group.rome_id = 'A1234'
        self.persona.project.job_search_length_months = 0
        if self.persona.project.kind == project_pb2.REORIENTATION:
            self.persona.project.kind = project_pb2.FIND_JOB
        self.assertGreater(2, self._score_persona(self.persona))
        mock_carif_get_trainings.assert_called_once_with('A1234', '35')

    @mock.patch(scoring.carif.__name__ + '.get_trainings')
    def test_three_stars(self, mock_carif_get_trainings):
        """The user has been searching for a job for 3 months."""
        mock_carif_get_trainings.return_value = self._many_trainings
        self.persona.project.job_search_length_months = 3
        self.assertEqual(3, self._score_persona(self.persona))

    @mock.patch(scoring.carif.__name__ + '.get_trainings')
    def test_one_month(self, mock_carif_get_trainings):
        """The user has been searching for a job for 1 month."""
        mock_carif_get_trainings.return_value = self._many_trainings
        self.persona.project.job_search_length_months = 1
        if self.persona.project.kind == project_pb2.REORIENTATION:
            self.persona.project.kind = project_pb2.FIND_JOB
        score = self._score_persona(self.persona)
        self.assertGreater(3, score)
        self.assertLess(0, score)

    @mock.patch(scoring.carif.__name__ + '.get_trainings')
    def test_reorientation(self, mock_carif_get_trainings):
        """The user is in reorientation."""
        mock_carif_get_trainings.return_value = self._many_trainings
        self.persona.project.kind = project_pb2.REORIENTATION
        self.assertEqual(3, self._score_persona(self.persona))

    @mock.patch(scoring.carif.__name__ + '.get_trainings')
    def test_no_trainings(self, mock_carif_get_trainings):
        """There are no trainings for this combination."""
        mock_carif_get_trainings.return_value = []
        self.assertEqual(0, self._score_persona(self.persona))


class ImproveYourNetworkScoringModelTestCase(ScoringModelTestBase('advice-improve-network')):
    """Unit test for the "Improve your network" scoring model."""

    def setUp(self):
        super(ImproveYourNetworkScoringModelTestCase, self).setUp()
        self.persona = self._random_persona().clone()

    def test_strong_network(self):
        """User already has a strong or good enough network."""
        if self.persona.project.network_estimate < 2:
            self.persona.project.network_estimate = 2
        score = self._score_persona(self.persona)
        self.assertLessEqual(score, 0, msg='Fail for "%s"' % self.persona.name)

    def test_network_is_best_application_mode(self):
        """User is in a job that hires a lot through network."""
        self.persona = _PERSONAS['malek'].clone()
        self.persona.project.network_estimate = 1
        self.persona.project.target_job.job_group.rome_id = 'A1234'
        self.persona.project.mobility.city.departement_id = '69'
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'applicationModes': {
                'R4Z92': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        }
                    ],
                }
            },
        })
        score = self._score_persona(self.persona)
        self.assertGreaterEqual(score, 3, msg='Fail for "%s"' % self.persona.name)

    def test_network_is_not_the_best_application_mode(self):
        """User is in a job that does not use network a lot to hire."""
        self.persona.project.network_estimate = 1
        self.persona.project.target_job.job_group.rome_id = 'A1234'
        self.persona.project.mobility.city.departement_id = '69'
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'applicationModes': {
                'R4Z92': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        }
                    ],
                }
            },
        })
        score = self._score_persona(self.persona)
        self.assertEqual(score, 2, msg='Fail for "%s"' % self.persona.name)

    def test_network_is_not_always_the_best_application_mode(self):
        """User is in a job that does not use only network to hire."""
        self.persona.project.network_estimate = 1
        self.persona.project.target_job.job_group.rome_id = 'A1234'
        self.persona.project.mobility.city.departement_id = '69'
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'applicationModes': {
                'Foo': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        }
                    ],
                },
                'Bar': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        }
                    ],
                }
            },
        })
        score = self._score_persona(self.persona)
        self.assertEqual(score, 2, msg='Fail for "%s"' % self.persona.name)


class ConstantScoreModelTestCase(ScoringModelTestBase('constant(2)')):
    """Unit test for the constant scoring model."""

    def test_random(self):
        """Check score on a random persona."""
        persona = self._random_persona()
        self.assertEqual(2, self._score_persona(persona), msg='Failed for "%s"' % persona.name)


class CommuteScoringModelTestCase(ScoringModelTestBase('advice-commute')):
    """Unit test for the "Commute" scoring model."""
    # TODO(guillaume): Add more tests when the scoring model takes the city into account.

    def setUp(self):
        super(CommuteScoringModelTestCase, self).setUp()
        self.persona = self._random_persona().clone()
        self.database.cities.insert_one({
            '_id': '69123',
            'longitude': 4.6965532,
            'latitude': 45.7179675
        })

        self.database.hiring_cities.insert_one({
            '_id': 'M1604',
            'hiringCities': [
                {
                    'offers': 10,
                    'city': {
                        'name': 'Brindas',
                        'longitude': 4.6965532,
                        'latitude': 45.7179675,
                        'population': 10000
                    }
                },
                {
                    'offers': 40,
                    'city': {
                        'name': 'Lyon',
                        'longitude': 4.8363116,
                        'latitude': 45.7640454,
                        'population': 400000
                    }
                },
                {
                    'offers': 40,
                    'city': {
                        'name': 'Saint-Priest',
                        'longitude': 4.9123846,
                        'latitude': 45.7013617,
                        'population': 20000
                    }
                },
                {
                    'offers': 40,
                    'city': {
                        'name': 'Vaulx-en-Velin',
                        'longitude': 4.8892431,
                        'latitude': 45.7775502,
                        'population': 10000
                    }
                }
            ]
        })

    def test_lyon(self):
        """Test that people in Lyon match."""
        self.persona.project.mobility.city.city_id = '69123'
        self.persona.project.target_job.job_group.rome_id = 'M1604'
        score = self._score_persona(self.persona)
        self.assertGreater(score, 1, msg='Fail for "%s"' % self.persona.name)

    def test_non_valid(self):
        """Test that people with a non-valid INSEE code should not get any commute advice."""
        self.persona.project.mobility.city.city_id = '691234'
        self.persona.project.target_job.job_group.rome_id = 'M1604'
        score = self._score_persona(self.persona)
        self.assertEqual(score, 0, msg='Fail for "%s"' % self.persona.name)

    def test_super_commute(self):
        """Test that people that wants to move and with super commute cities have score 3."""
        self.persona.project.mobility.city.city_id = '69123'
        self.persona.project.target_job.job_group.rome_id = 'M1604'
        if self.persona.project.mobility.area_type <= geo_pb2.CITY:
            self.persona.project.mobility.area_type = geo_pb2.DEPARTEMENT
        score = self._score_persona(self.persona)
        self.assertEqual(score, 3, msg='Fail for "%s"' % self.persona.name)

    def test_extra_data(self):
        """Compute extra data."""
        self.persona.project.mobility.city.city_id = '69123'
        self.persona.project.target_job.job_group.rome_id = 'M1604'
        project = self.persona.scoring_project(self.database)
        result = self.model.compute_extra_data(project)
        self.assertGreater(len(result.cities), 1, msg='Failed for "%s"' % self.persona.name)


class PersonasTestCase(unittest.TestCase):
    """Tests all scoring models and all personas."""

    @mock.patch(scoring.carif.__name__ + '.get_trainings')
    def test_run_all(self, mock_carif_get_trainings):
        """Run all scoring models on all personas."""
        mock_carif_get_trainings.return_value = [
            training_pb2.Training(),
            training_pb2.Training(),
            training_pb2.Training(),
        ]
        database = mongomock.MongoClient().test
        _load_json_to_mongo(database, 'job_group_info')
        _load_json_to_mongo(database, 'local_diagnosis')
        _load_json_to_mongo(database, 'associations')
        _load_json_to_mongo(database, 'volunteering_missions')
        _load_json_to_mongo(database, 'hiring_cities')
        _load_json_to_mongo(database, 'cities')
        _load_json_to_mongo(database, 'specific_to_job_advice')
        scores = collections.defaultdict(lambda: collections.defaultdict(float))
        # Mock the "now" date so that scoring models that are based on time
        # (like "Right timing") are deterministic.
        now = datetime.datetime(2016, 9, 27)
        for model_name in list(scoring.SCORING_MODELS.keys()):
            model = scoring.get_scoring_model(model_name)
            self.assertTrue(model, msg=model_name)
            scores[model_name] = {}
            for name, persona in _PERSONAS.items():
                scores[model_name][name] = model.score(
                    persona.scoring_project(database, now=now))
                self.assertIsInstance(
                    scores[model_name][name],
                    numbers.Number,
                    msg='while using the model "%s" to score "%s"'
                    % (model_name, name))

        for name in _PERSONAS:
            persona_scores = [
                max(model_scores[name], 0)
                for model_scores in scores.values()]
            self.assertLess(
                1, len(set(persona_scores)),
                msg='Persona "%s" has the same score across all models.' % name)

        for model_name, model_scores in scores.items():
            model = scoring.SCORING_MODELS[model_name]
            if isinstance(model, scoring.ConstantScoreModel):
                continue
            self.assertLess(
                1, len(set(model_scores.values())),
                msg='Model "%s" has the same score for all personas.' % model_name)


class LifeBalanceTestCase(ScoringModelTestBase('advice-life-balance')):
    """Unit tests for the "Work/Life balance" advice."""

    def test_short_searching(self):
        """The user does not have a diploma problem."""
        persona = self._random_persona().clone()
        if persona.project.job_search_length_months > 3:
            persona.project.job_search_length_months = 2
        persona.user_profile.has_handicap = False
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s"' % persona.name)

    def test_handicaped(self):
        """The user has a handicap."""
        persona = self._random_persona().clone()
        persona.user_profile.has_handicap = True
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s"' % persona.name)

    def test_long_searching(self):
        """The user does not have a diploma problem."""
        persona = self._random_persona().clone()
        if persona.project.job_search_length_months < 4:
            persona.project.job_search_length_months = 4
        persona.user_profile.has_handicap = False
        score = self._score_persona(persona)
        self.assertEqual(score, 1, msg='Failed for "%s"' % persona.name)


class AdviceVaeTestCase(ScoringModelTestBase('advice-vae')):
    """Unit tests for the "vae" advice."""

    def test_experiemented(self):
        """The user is experimented and think he has enough diplomas."""
        persona = self._random_persona().clone()
        persona.project.seniority = project_pb2.EXPERT
        persona.project.training_fulfillment_estimate = project_pb2.ENOUGH_EXPERIENCE
        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s"' % persona.name)

    def test_frustrated_by_trainings_and_is_senior(self):
        """The user is frustrated by training and is senior."""
        persona = self._random_persona().clone()
        persona.user_profile.frustrations.append(user_pb2.TRAINING)
        persona.project.seniority = project_pb2.SENIOR
        score = self._score_persona(persona)
        self.assertGreaterEqual(score, 2, msg='Failed for "%s"' % persona.name)

    def test_not_matching(self):
        """The user does not have a diploma problem."""
        persona = self._random_persona().clone()
        persona.project.training_fulfillment_estimate = project_pb2.ENOUGH_DIPLOMAS
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s"' % persona.name)

    def test_frustrated_no_experience(self):
        """The user is frustrated by trainings, has no experience and his diploma is unsure."""
        persona = self._random_persona().clone()
        persona.user_profile.frustrations.append(user_pb2.TRAINING)
        persona.project.seniority = project_pb2.JUNIOR
        persona.project.training_fulfillment_estimate = project_pb2.TRAINING_FULFILLMENT_NOT_SURE
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s"' % persona.name)

    def test_has_enough_diplomas(self):
        """The user is frustrated by trainings but is expert and has enough diplomas."""
        persona = self._random_persona().clone()
        persona.user_profile.frustrations.append(user_pb2.TRAINING)
        persona.project.seniority = project_pb2.EXPERT
        persona.project.training_fulfillment_estimate = project_pb2.ENOUGH_DIPLOMAS
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s"' % persona.name)


class AdviceSeniorTestCase(ScoringModelTestBase('advice-senior')):
    """Unit tests for the "Senior" advice."""

    def test_match_discriminated(self):
        """The user is over 40 years old and feels discriminated so this should match."""
        persona = self._random_persona().clone()
        if persona.user_profile.year_of_birth > datetime.date.today().year - 41:
            persona.user_profile.year_of_birth = datetime.date.today().year - 41
        persona.user_profile.frustrations.append(user_pb2.AGE_DISCRIMINATION)
        score = self._score_persona(persona)
        self.assertEqual(score, 2, msg='Failed for "%s"' % persona.name)

    def test_match_old(self):
        """The user is over 50 years old so the advice should match."""
        persona = self._random_persona().clone()
        if persona.user_profile.year_of_birth > datetime.date.today().year - 50:
            persona.user_profile.year_of_birth = datetime.date.today().year - 50
        score = self._score_persona(persona)
        self.assertEqual(score, 2, msg='Failed for "%s"' % persona.name)

    def test_no_match(self):
        """The user is young so the advice should not match."""
        persona = self._random_persona().clone()
        if persona.user_profile.year_of_birth < datetime.date.today().year - 35:
            persona.user_profile.year_of_birth = datetime.date.today().year - 35
        score = self._score_persona(persona)
        self.assertLessEqual(score, 0, msg='Failed for "%s"' % persona.name)


class AdviceLessApplicationsTestCase(ScoringModelTestBase('advice-less-applications')):
    """Unit tests for the "Apply less" advice."""

    def test_match(self):
        """The user applies a lot so the advice should match."""
        persona = self._random_persona().clone()
        if persona.project.weekly_applications_estimate != project_pb2.A_LOT and \
                persona.project.weekly_applications_estimate != project_pb2.DECENT_AMOUNT:
            persona.project.weekly_applications_estimate = project_pb2.DECENT_AMOUNT
        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s"' % persona.name)

    def test_no_match(self):
        """The user does not apply a lot so the advice should not match."""
        persona = self._random_persona().clone()
        if persona.project.weekly_applications_estimate == project_pb2.DECENT_AMOUNT or \
                persona.project.weekly_applications_estimate == project_pb2.A_LOT:
            persona.project.weekly_applications_estimate = project_pb2.SOME
        score = self._score_persona(persona)
        self.assertLessEqual(score, 0, msg='Failed for "%s"' % persona.name)


class AdviceAssociationHelpTestCase(ScoringModelTestBase('advice-association-help')):
    """Unit tests for the "Find an association to help you" advice."""

    def test_no_data(self):
        """No associations data."""
        persona = self._random_persona().clone()
        score = self._score_persona(persona)
        self.assertLessEqual(score, 0, msg='Failed for "%s"' % persona.name)

    def test_motivated(self):
        """User is motivated."""
        persona = self._random_persona().clone()
        self.database.associations.insert_one({'name': 'SNC'})
        del persona.user_profile.frustrations[:]
        if persona.project.job_search_length_months >= 12:
            persona.project.job_search_length_months = 11
        score = self._score_persona(persona)
        self.assertEqual(2, score, msg='Failed for "%s"' % persona.name)

    def test_need_motivation(self):
        """User needs motivation."""
        persona = self._random_persona().clone()
        self.database.associations.insert_one({'name': 'SNC'})
        persona.user_profile.frustrations.append(user_pb2.MOTIVATION)
        score = self._score_persona(persona)
        self.assertEqual(3, score, msg='Failed for "%s"' % persona.name)

    def test_many_assos_and_long_search(self):
        """User searches for a long time and there are a lot of associations."""
        persona = self._random_persona().clone()
        self.database.associations.insert_many(
            [{'name': 'SNC'}, {'name': 'SND'}, {'name': 'SNE'}, {'name': 'SNF'}])
        persona.project.job_search_length_months = 6
        score = self._score_persona(persona)
        self.assertEqual(3, score, msg='Failed for "%s"' % persona.name)

    def test_very_long_search(self):
        """User searches for a very long time."""
        persona = self._random_persona().clone()
        self.database.associations.insert_one({'name': 'SNC'})
        persona.project.job_search_length_months = 12
        score = self._score_persona(persona)
        self.assertEqual(3, score, msg='Failed for "%s"' % persona.name)


class AdviceBetterJobInGroupTestCase(ScoringModelTestBase('advice-better-job-in-group')):
    """Unit tests for the "Find a better job in job group" advice."""

    def test_no_data(self):
        """No data for job group."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'A1234'
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'jobs': [
                {'codeOgr': '1234', 'name': 'foo'},
                {'codeOgr': '5678', 'name': 'foo'},
            ],
        })
        score = self._score_persona(persona)
        self.assertLessEqual(score, 0, msg='Failed for "%s"' % persona.name)

    def test_should_try_other_job(self):
        """There's a job with way more offers, and the user wants to reorient."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'A1234'
        persona.project.target_job.code_ogr = '5678'
        persona.project.kind = project_pb2.REORIENTATION
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'jobs': [
                {'codeOgr': '1234', 'name': 'foo'},
                {'codeOgr': '5678', 'name': 'foo'},
            ],
            'requirements': {
                'specificJobs': [{
                    'codeOgr': '1234',
                    'percentSuggested': 100,
                }],
            },
        })
        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s"' % persona.name)

    def test_already_best_job(self):
        """User is targetting the best job in their group."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'A1234'
        persona.project.target_job.code_ogr = '1234'
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'jobs': [
                {'codeOgr': '1234', 'name': 'foo'},
                {'codeOgr': '5678', 'name': 'foo'},
            ],
            'requirements': {
                'specificJobs': [{
                    'codeOgr': '1234',
                    'percentSuggested': 100,
                }],
            },
        })
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s"' % persona.name)

    def test_already_good_job(self):
        """User is targetting a correct job in their group, but not the best."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'A1234'
        persona.project.target_job.code_ogr = '1234'
        persona.project.job_search_length_months = 2
        persona.project.kind = project_pb2.FIND_A_FIRST_JOB
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'jobs': [
                {'codeOgr': '1234', 'name': 'foo'},
                {'codeOgr': '5678', 'name': 'foo'},
            ],
            'requirements': {
                'specificJobs': [
                    {
                        'codeOgr': '5678',
                        'percentSuggested': 50,
                    },
                    {
                        'codeOgr': '1234',
                        'percentSuggested': 45,
                    },
                ],
            },
        })
        score = self._score_persona(persona)
        self.assertEqual(score, 2, msg='Failed for "%s"' % persona.name)


class VolunteerAdviceTestCase(ScoringModelTestBase('advice-volunteer')):
    """Unit tests for the "Volunteer" advice."""

    def setUp(self):
        super(VolunteerAdviceTestCase, self).setUp()
        self.database.volunteering_missions.insert_one({
            '_id': '75',
            'missions': [{'title': 'Mission n°1'}],
        })

    def test_no_mission_data(self):
        """No volunteering missions data."""
        persona = self._random_persona().clone()
        persona.project.mobility.city.departement_id = '56'

        score = self._score_persona(persona)

        self.assertEqual(score, 0, msg='Failed for "%s"' % persona.name)

    def test_very_long_search(self):
        """Job seeker has been searching for a looong time."""
        persona = self._random_persona().clone()
        persona.project.mobility.city.departement_id = '75'
        persona.project.job_search_length_months = 20

        score = self._score_persona(persona)

        self.assertEqual(score, 2, msg='Failed for "%s"' % persona.name)

    def test_just_started_searching(self):
        """Job seeker has just started searching."""
        persona = self._random_persona().clone()
        persona.project.mobility.city.departement_id = '75'
        persona.project.job_search_length_months = 1

        score = self._score_persona(persona)

        self.assertEqual(score, 1, msg='Failed for "%s"' % persona.name)


class SpontaneousApplicationScoringModelTestCase(
        ScoringModelTestBase('advice-spontaneous-application')):
    """Unit tests for the "Send spontaneous applications" chantier."""

    def test_best_channel(self):
        """User is in a market where spontaneous application is the best channel."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'A1234'
        persona.project.mobility.city.departement_id = '69'
        persona.project.job_search_length_months = 2
        persona.project.weekly_applications_estimate = project_pb2.LESS_THAN_2
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'applicationModes': {
                'R4Z92': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        }
                    ],
                }
            },
        })
        score = self._score_persona(persona)

        self.assertEqual(score, 3, msg='Failed for "%s"' % persona.name)

    def test_second_best_channel(self):
        """User is in a market where spontaneous application is the second best channel."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'A1234'
        persona.project.mobility.city.departement_id = '69'
        persona.project.job_search_length_months = 2
        persona.project.weekly_applications_estimate = project_pb2.LESS_THAN_2
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'applicationModes': {
                'R4Z92': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        }
                    ],
                }
            },
        })
        score = self._score_persona(persona)

        self.assertEqual(score, 2, msg='Failed for "%s"' % persona.name)

    def test_not_best_channel(self):
        """User is in a market where spontaneous application is not the best channel."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'A1234'
        persona.project.mobility.city.departement_id = '69'
        persona.project.job_search_length_months = 2
        persona.project.weekly_applications_estimate = project_pb2.LESS_THAN_2
        self.database.job_group_info.insert_one({
            '_id': 'A1234',
            'applicationModes': {
                'R4Z92': {
                    'modes': [
                        {
                            'percentage': 36.38,
                            'mode': 'UNDEFINED_APPLICATION_MODE'
                        },
                        {
                            'percentage': 29.46,
                            'mode': 'PLACEMENT_AGENCY'
                        },
                        {
                            'percentage': 18.38,
                            'mode': 'SPONTANEOUS_APPLICATION'
                        },
                        {
                            'percentage': 15.78,
                            'mode': 'PERSONAL_OR_PROFESSIONAL_CONTACTS'
                        }
                    ],
                }
            },
        })
        score = self._score_persona(persona)

        self.assertEqual(score, 0, msg='Failed for "%s"' % persona.name)


class AdviceJobBoardsTestCase(ScoringModelTestBase('advice-job-boards')):
    """Unit tests for the "Other Work Environments" advice."""

    def test_frustrated(self):
        """Frustrated by not enough offers."""
        persona = self._random_persona().clone()
        persona.user_profile.frustrations.append(user_pb2.NO_OFFERS)

        score = self._score_persona(persona)

        self.assertGreaterEqual(score, 2, msg='Failed for "%s"' % persona.name)

    def test_lot_of_offers(self):
        """User has many offers already."""
        persona = self._random_persona().clone()
        del persona.user_profile.frustrations[:]
        persona.project.weekly_offers_estimate = project_pb2.A_LOT

        score = self._score_persona(persona)

        # We do want to show the chantier but not pre-select it.
        self.assertEqual(1, score, msg='Failed for "%s"' % persona.name)

    def test_extra_data(self):
        """Compute extra data."""
        persona = self._random_persona().clone()
        project = persona.scoring_project(self.database)
        self.database.jobboards.insert_one({'title': 'Remix Jobs'})
        result = self.model.compute_extra_data(project)
        self.assertTrue(result, msg='Failed for "%s"' % persona.name)
        self.assertEqual('Remix Jobs', result.job_board_title, msg='Failedfor "%s"' % persona.name)

    def test_filter_data(self):
        """Get the job board with the most filters."""
        persona = self._random_persona().clone()
        persona.project.mobility.city.departement_id = '69'
        project = persona.scoring_project(self.database)
        self.database.jobboards.insert_many([
            {'title': 'Remix Jobs'},
            {'title': 'Specialized for me', 'filters': ['for-departement(69)']},
            {'title': 'Specialized NOT for me', 'filters': ['for-departement(31)']},
        ])
        result = self.model.compute_extra_data(project)
        self.assertTrue(result)
        self.assertEqual('Specialized for me', result.job_board_title)

    def test_filter_pole_emploi(self):
        """Never show Pôle emploi,"""
        persona = self._random_persona().clone()
        persona.project.mobility.city.departement_id = '69'
        project = persona.scoring_project(self.database)
        self.database.jobboards.insert_many([
            {'title': 'Pôle emploi', 'isWellKnown': True},
            {'title': 'Remix Jobs'},
        ])
        result = self.model.compute_extra_data(project)
        self.assertTrue(result)
        self.assertEqual('Remix Jobs', result.job_board_title)


class AdviceSeasonalRelocateTestCase(ScoringModelTestBase('advice-seasonal-relocate')):
    """Unit tests for the "Advice Seasonal Relocate" advice."""

    def test_older(self):
        """Do not trigger for older people."""
        persona = self._random_persona().clone()
        if persona.user_profile.year_of_birth > datetime.date.today().year - 36:
            persona.user_profile.year_of_birth = datetime.date.today().year - 36
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_region(self):
        """Do not trigger for people who's mobility is below "COUNTRY"."""
        persona = self._random_persona().clone()
        if persona.project.mobility.area_type >= geo_pb2.COUNTRY:
            persona.project.mobility.area_type = geo_pb2.REGION
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_children(self):
        """Do not trigger for people who have children."""
        persona = self._random_persona().clone()
        persona.user_profile.family_situation = user_pb2.FAMILY_WITH_KIDS
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_diplomas(self):
        """Do not trigger for people who have diplomas."""
        persona = self._random_persona().clone()
        if persona.user_profile.highest_degree <= job_pb2.BTS_DUT_DEUG:
            persona.user_profile.highest_degree = job_pb2.LICENCE_MAITRISE
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_young_no_diploma(self):
        """Young mobile single people without advanced diplomas should trigger."""
        persona = self._random_persona().clone()
        persona.project.mobility.area_type = geo_pb2.COUNTRY
        if persona.user_profile.year_of_birth < datetime.date.today().year - 28:
            persona.user_profile.year_of_birth = datetime.date.today().year - 28
        if persona.user_profile.year_of_birth > datetime.date.today().year - 25:
            persona.user_profile.year_of_birth = datetime.date.today().year - 25
        if persona.user_profile.highest_degree > job_pb2.BAC_BACPRO:
            persona.user_profile.highest_degree = job_pb2.BAC_BACPRO
        persona.user_profile.family_situation = user_pb2.SINGLE
        if persona.project.employment_types == [job_pb2.CDI]:
            persona.project.employment_types.append(job_pb2.CDD_LESS_EQUAL_3_MONTHS)

        score = self._score_persona(persona)
        self.assertEqual(score, 2, msg='Failed for "%s":' % persona.name)

    def test_very_young_no_diploma(self):
        """Very mobile single people without advanced diplomas should trigger high."""
        persona = self._random_persona().clone()
        persona.project.mobility.area_type = geo_pb2.COUNTRY
        if persona.user_profile.year_of_birth < datetime.date.today().year - 22:
            persona.user_profile.year_of_birth = datetime.date.today().year - 22
        if persona.user_profile.highest_degree > job_pb2.BAC_BACPRO:
            persona.user_profile.highest_degree = job_pb2.BAC_BACPRO
        if persona.project.employment_types == [job_pb2.CDI]:
            persona.project.employment_types.append(job_pb2.CDD_LESS_EQUAL_3_MONTHS)
        persona.user_profile.family_situation = user_pb2.SINGLE

        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s":' % persona.name)


class AdviceOtherWorkEnvTestCase(ScoringModelTestBase('advice-other-work-env')):
    """Unit tests for the "Other Work Environments" advice."""

    def test_no_job_group_info(self):
        """Does not trigger if we are missing environment data."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'M1607'
        self.database.job_group_info.insert_one({'_id': 'M1607'})

        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_with_other_structures(self):
        """Triggers if multiple structures."""
        self.database.job_group_info.insert_one({
            '_id': 'M1607',
            'workEnvironmentKeywords': {'structures': ['Kmenistan', 'Key']},
        })
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'M1607'

        score = self._score_persona(persona)
        self.assertEqual(score, 2, msg='Failed for "%s":' % persona.name)

    def test_with_only_one_structure_and_one_sector(self):
        """Only one structure and one sector."""
        self.database.job_group_info.insert_one({
            '_id': 'M1607',
            'workEnvironmentKeywords': {
                'structures': ['Kmenistan'],
                'sectors': ['Toise'],
            },
        })
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'M1607'

        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)


class AdviceImproveInterviewTestCase(ScoringModelTestBase('advice-improve-interview')):
    """Unit tests for the "Improve Your Interview Skills" advice."""

    def test_not_enough_interviews(self):
        """Users does not get enough interviews."""
        persona = self._random_persona().clone()
        if persona.project.job_search_length_months < 3:
            persona.project.job_search_length_months = 3
        if persona.project.job_search_length_months > 6:
            persona.project.job_search_length_months = 6
        persona.project.total_interview_count = 1
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_many_interviews(self):
        """Users has maximum interviews."""
        persona = self._random_persona().clone()
        persona.project.total_interview_count = 21
        persona.project.job_search_length_months = 2
        if persona.project.job_search_length_months > 6:
            persona.project.job_search_length_months = 6
        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s":' % persona.name)

    def test_many_interviews_long_time(self):
        """Users has maximum interviews."""
        persona = self._random_persona().clone()
        persona.project.total_interview_count = 21
        if persona.project.job_search_length_months > 6:
            persona.project.job_search_length_months = 6
        score = self._score_persona(persona)
        self.assertGreaterEqual(score, 3, msg='Failed for "%s":' % persona.name)


class AdviceImproveResumeTestCase(ScoringModelTestBase('advice-improve-resume')):
    """Unit tests for the "Improve Your Resume" advice."""

    def test_not_enough_interviews(self):
        """Users does not get enough interviews."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'I1202'
        persona.project.mobility.city.departement_id = '14'
        if persona.project.job_search_length_months < 3:
            persona.project.job_search_length_months = 3
        if persona.project.job_search_length_months > 6:
            persona.project.job_search_length_months = 6
        if persona.project.weekly_applications_estimate < project_pb2.DECENT_AMOUNT:
            persona.project.weekly_applications_estimate = project_pb2.DECENT_AMOUNT
        persona.project.total_interview_count = 1
        self.database.local_diagnosis.insert_one({
            '_id': '14:I1202',
            'imt': {
                'yearlyAvgOffersDenominator': 10,
                'yearlyAvgOffersPer10Candidates': 2,
            },
        })
        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s":' % persona.name)

    def test_many_interviews(self):
        """Users has maximum interviews."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'I1202'
        persona.project.mobility.city.departement_id = '14'
        persona.project.weekly_applications_estimate = project_pb2.DECENT_AMOUNT
        persona.project.total_interview_count = 21
        self.database.local_diagnosis.insert_one({
            '_id': '14:I1202',
            'imt': {
                'yearlyAvgOffersDenominator': 10,
                'yearlyAvgOffersPer10Candidates': 2,
            },
        })
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_no_applications(self):
        """Users has never sent an application."""
        persona = self._random_persona().clone()
        persona.project.total_interview_count = -1
        persona.project.weekly_applications_estimate = project_pb2.LESS_THAN_2
        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_imt_data_missing(self):
        """Users does not get enough interview although IMT is missing."""
        persona = self._random_persona().clone()
        if persona.project.job_search_length_months < 3:
            persona.project.job_search_length_months = 3
        if persona.project.job_search_length_months > 6:
            persona.project.job_search_length_months = 6
        if persona.project.weekly_applications_estimate < project_pb2.DECENT_AMOUNT:
            persona.project.weekly_applications_estimate = project_pb2.DECENT_AMOUNT
        persona.project.total_interview_count = 1
        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s":' % persona.name)


class AdviceWowBakerTestCase(ScoringModelTestBase('advice-wow-baker')):
    """Unit tests for the "Wow Baker" advice."""

    def test_not_baker(self):
        """Does not trigger for non baker."""
        persona = self._random_persona().clone()
        if persona.project.target_job.job_group.rome_id == 'D1102':
            persona.project.target_job.job_group.rome_id = 'M1607'

        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_chief_baker(self):
        """Does not trigger for a chief baker."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'D1102'
        persona.project.target_job.code_ogr = '12006'

        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_baker_not_chief(self):
        """Does not trigger for a chief baker."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'D1102'
        if persona.project.target_job.code_ogr == '12006':
            persona.project.target_job.code_ogr = '10868'

        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s":' % persona.name)


class AdviceSpecificToJobTestCase(ScoringModelTestBase('advice-specific-to-job')):
    """Unit tests for the "Specicif to Job" advice."""

    def setUp(self):
        super(AdviceSpecificToJobTestCase, self).setUp()
        self.database.specific_to_job_advice.insert_one({
            'title': 'Présentez-vous au chef boulanger dès son arrivée tôt le matin',
            'filters': ['for-job-group(D1102)', 'not-for-job(12006)'],
            'cardText':
            'Allez à la boulangerie la veille pour savoir à quelle '
            'heure arrive le chef boulanger.',
            'expandedCardHeader': "Voilà ce qu'il faut faire",
            'expandedCardItems': [
                'Se présenter aux boulangers entre 4h et 7h du matin.',
                'Demander au vendeur / à la vendeuse à quelle heure arrive le chef le matin',
                'Contacter les fournisseurs de farine locaux : ils connaissent '
                'tous les boulangers du coin et sauront où il y a des '
                'embauches.',
            ],
        })

    def test_not_baker(self):
        """Does not trigger for non baker."""
        persona = self._random_persona().clone()
        if persona.project.target_job.job_group.rome_id == 'D1102':
            persona.project.target_job.job_group.rome_id = 'M1607'

        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_chief_baker(self):
        """Does not trigger for a chief baker."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'D1102'
        persona.project.target_job.code_ogr = '12006'

        score = self._score_persona(persona)
        self.assertEqual(score, 0, msg='Failed for "%s":' % persona.name)

    def test_baker_not_chief(self):
        """Trigger for a baker that is not a chief baker."""
        persona = self._random_persona().clone()
        persona.project.target_job.job_group.rome_id = 'D1102'
        if persona.project.target_job.code_ogr == '12006':
            persona.project.target_job.code_ogr = '10868'

        score = self._score_persona(persona)
        self.assertEqual(score, 3, msg='Failed for "%s":' % persona.name)


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
