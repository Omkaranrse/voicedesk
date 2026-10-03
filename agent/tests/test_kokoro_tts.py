from voicedesk.kokoro_tts import KokoroTTS, split_sentences_stream


def test_sentence_splitting_basic():
    text = "Hello, this is VoiceDesk clinic. How can I help you today?"
    sents, rest = split_sentences_stream(text, is_final=True)
    assert sents == ["Hello, this is VoiceDesk clinic.", "How can I help you today?"]
    assert rest == ""


def test_sentence_splitting_with_times():
    text = "Available slots on Monday are 10:00, 11:00, and 14:00. Would you like to book one?"
    sents, rest = split_sentences_stream(text, is_final=True)
    assert sents == [
        "Available slots on Monday are 10:00, 11:00, and 14:00.",
        "Would you like to book one?",
    ]
    assert rest == ""


def test_sentence_splitting_streaming_partial():
    # Incomplete sentence should stay in buffer if < 15 chars or no punctuation
    sents, rest = split_sentences_stream("Available slots", is_final=False)
    assert sents == []
    assert rest == "Available slots"

    # Terminal punctuation should emit sentence immediately
    sents, rest = split_sentences_stream(
        "Available slots are at 10:00. ", is_final=False
    )
    assert sents == ["Available slots are at 10:00."]
    assert rest == ""


def test_kokoro_tts_init():
    tts = KokoroTTS()
    assert tts.model == "kokoro"
    assert tts.provider == "kokoro"
    assert tts.sample_rate == 24000
    assert tts.num_channels == 1
    assert tts.capabilities.streaming is True
