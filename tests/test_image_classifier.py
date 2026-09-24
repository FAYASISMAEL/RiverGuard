from io import BytesIO
from unittest.mock import Mock
import json
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import ai, config
from backend.app.image_classifier import Prediction, aggregate, GeminiImageClassifier
from tests.test_api import payload


def photo(color='blue'):
    data = BytesIO()
    Image.new('RGB', (40, 40), color).save(data, 'PNG')
    return data.getvalue()


def files(count=1):
    return [('images[]', (f'evidence-{i}.png', photo(), 'image/png')) for i in range(count)]


@pytest.mark.parametrize('category', ['Dead Fish','Plastic / Solid Waste','Foam','Oil / Fuel','Water Discoloration'])
def test_visual_category_contract(monkeypatch, category):
    provider = Mock()
    provider.classify.return_value = [Prediction(category=category, confidence=.91)]
    monkeypatch.setattr(ai, 'get_classifier', lambda: provider)
    with TestClient(app) as client:
        response = client.post('/api/ai/classify-contamination', files=files())
        assert response.status_code == 200
        assert response.json()['suggested_category'] == category
        assert response.json()['auto_select'] is True
        assert len(provider.classify.call_args.args[0]) == 1


def test_all_images_majority_and_threshold(monkeypatch):
    provider = Mock()
    provider.classify.return_value = [Prediction(category='Plastic / Solid Waste',confidence=.92), Prediction(category='Plastic / Solid Waste',confidence=.86), Prediction(category='Water Discoloration',confidence=.55)]
    monkeypatch.setattr(ai, 'get_classifier', lambda: provider)
    monkeypatch.setattr(config, 'AI_CONFIDENCE_THRESHOLD', .9)
    with TestClient(app) as client:
        response = client.post('/api/ai/classify-contamination', files=files(3)).json()
        assert len(provider.classify.call_args.args[0]) == 3
        assert len(response['image_results']) == 3
        assert response['suggested_category'] == 'Plastic / Solid Waste'
        assert response['confidence'] == .89
        assert response['auto_select'] is False


@pytest.mark.parametrize('scenario', ['unrelated', 'blurry', 'low-confidence', 'tie'])
def test_unclear_results_never_auto_select(monkeypatch, scenario):
    values = [Prediction(category='Other / Unclear', confidence=.2)]
    if scenario == 'low-confidence': values = [Prediction(category='Dead Fish', confidence=.6)]
    if scenario == 'tie': values = [Prediction(category='Dead Fish', confidence=.95), Prediction(category='Foam', confidence=.9)]
    provider = Mock()
    provider.classify.return_value = values
    monkeypatch.setattr(ai, 'get_classifier', lambda: provider)
    with TestClient(app) as client:
        result = client.post('/api/ai/classify-contamination', files=files(len(values))).json()
        assert not result['auto_select']


def test_provider_unavailable_and_invalid_upload(monkeypatch):
    provider = Mock()
    provider.classify.side_effect = TimeoutError()
    monkeypatch.setattr(ai, 'get_classifier', lambda: provider)
    with TestClient(app) as client:
        result = client.post('/api/ai/classify-contamination', files=files())
        assert result.status_code == 200
        assert result.json()['success'] is False
        assert 'manually' in result.json()['message']
        assert client.post('/api/reports',json=payload()).status_code == 201
        assert client.post('/api/ai/classify-contamination',files=[('images[]',('bad.jpg',b'not an image','image/jpeg'))]).status_code == 422
        assert client.post('/api/ai/classify-contamination',files=files(config.MAX_IMAGES_PER_REPORT+1)).status_code == 422
        monkeypatch.setattr(config, 'AI_MAX_BATCH_BYTES', 1)
        assert client.post('/api/ai/classify-contamination',files=files()).status_code == 413


@pytest.mark.parametrize('final,source', [('Dead Fish','AI_CONFIRMED'),('Water Discoloration','USER_CORRECTED')])
def test_report_retains_original_suggestion_and_final_choice(final, source):
    with TestClient(app) as client:
        upload = client.post('/api/uploads',files={'file':('photo.png',photo(),'image/png')}).json()
        data = payload()
        data.update(contamination_type=final, image_urls=[upload['image_url']], ai_image_results=[{'category':'Dead Fish','confidence':.91}])
        response = client.post('/api/reports',json=data)
        assert response.status_code == 201, response.text
        report = response.json()
        assert report['status'] == 'UNVERIFIED'
        assert report['ai_detected_category'] == 'Dead Fish'
        assert report['ai_confidence'] == .91
        assert report['final_category'] == final
        assert report['category_source'] == source
        again = client.get('/api/reports/'+report['id']).json()
        assert again['category_source'] == source
        data['ai_image_results'].append({'category':'Foam','confidence':.9})
        assert client.post('/api/reports',json=data).status_code == 422


def test_gemini_adapter_sends_every_image_and_validates_response(monkeypatch):
    from backend.app import image_classifier
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps([{'category':'Foam','confidence':.9},{'category':'Foam','confidence':.8}])}]}}]}).encode()
    transport = Mock(return_value=response)
    monkeypatch.setattr(image_classifier, 'urlopen', transport)
    result = GeminiImageClassifier().classify([b'image-one',b'image-two'])
    assert aggregate(result)['confidence'] == .85
    body = json.loads(transport.call_args.args[0].data)
    assert len(body['contents'][0]['parts']) == 3
    response.read.return_value = b'{"candidates":[]}'
    with pytest.raises(IndexError): GeminiImageClassifier().classify([b'image'])

@pytest.mark.parametrize('kind', ['timeout', 'network', 'overloaded', 'rate-limit'])
def test_transient_inference_failure_retries_once(monkeypatch, kind):
    from urllib.error import HTTPError, URLError
    from unittest.mock import MagicMock
    from backend.app import image_classifier
    failures = {'timeout':TimeoutError(), 'network':URLError('connection reset'),
                'overloaded':HTTPError('https://provider.invalid',503,'busy',None,None),
                'rate-limit':HTTPError('https://provider.invalid',429,'busy',None,None)}
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b'{"ok":true}'
    transport = Mock(side_effect=[failures[kind], response])
    monkeypatch.setattr(image_classifier, 'urlopen', transport)
    monkeypatch.setattr(image_classifier.time, 'sleep', lambda _: None)
    assert image_classifier.request_prediction(Mock()) == {'ok':True}
    assert transport.call_count == 2


def test_inference_retry_is_bounded_and_auth_errors_are_not_retried(monkeypatch):
    from urllib.error import HTTPError
    from backend.app import image_classifier
    transport = Mock(side_effect=TimeoutError())
    monkeypatch.setattr(image_classifier, 'urlopen', transport)
    monkeypatch.setattr(image_classifier.time, 'sleep', lambda _: None)
    with pytest.raises(TimeoutError): image_classifier.request_prediction(Mock())
    assert transport.call_count == 2
    transport.reset_mock()
    transport.side_effect = HTTPError('https://provider.invalid',403,'denied',None,None)
    with pytest.raises(HTTPError): image_classifier.request_prediction(Mock())
    assert transport.call_count == 1
