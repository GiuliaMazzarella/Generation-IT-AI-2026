import builtins
import pytest
from main import main

class DummyWeather:
    def __init__(self, temp):
        self.temperature = temp
    def __str__(self):
        return f"Dummy {self.temperature}"

# Helper to simulate input sequences
class InputSimulator:
    def __init__(self, inputs):
        self._iter = iter(inputs)
    def __call__(self, prompt=''):
        try:
            return next(self._iter)
        except StopIteration:
            raise EOFError


def test_interactive_success_then_exit(monkeypatch, capsys):
    # Simula: 'Milano' -> (Weather) -> 'n' per uscire
    seq = ['Milano', 'n']
    monkeypatch.setattr('main.get_weather_by_city', lambda city: DummyWeather(10))
    monkeypatch.setattr('builtins.input', InputSimulator(seq))

    main()
    out = capsys.readouterr().out
    assert 'Temperatura' in out or 'Dummy 10' in out
    assert 'Uscita.' in out


def test_interactive_not_found_then_retry(monkeypatch, capsys):
    # Simula: '347f' -> None, risposta 's' -> 'Milano' -> 'n'
    seq = ['347f', 's', 'Milano', 'n']
    def fake_get_weather(city):
        if city == '347f':
            print("❌ Città non trovata. Riprova.")
            return None
        return DummyWeather(8)
    monkeypatch.setattr('main.get_weather_by_city', fake_get_weather)
    monkeypatch.setattr('builtins.input', InputSimulator(seq))

    main()
    out = capsys.readouterr().out
    assert 'Città non trovata' in out
    assert 'Dummy 8' in out


def test_interactive_invalid_answer_reprompts(monkeypatch, capsys):
    # Simula: 'Milano' -> Weather -> risposta 'forse' -> 'n'
    seq = ['Milano', 'forse', 'n']
    monkeypatch.setattr('main.get_weather_by_city', lambda city: DummyWeather(6))
    monkeypatch.setattr('builtins.input', InputSimulator(seq))

    main()
    out = capsys.readouterr().out
    assert 'Risposta non valida' in out


def test_interactive_direct_exit(monkeypatch, capsys):
    seq = ['exit']
    monkeypatch.setattr('builtins.input', InputSimulator(seq))

    main()
    out = capsys.readouterr().out
    assert 'Uscita.' in out


def test_interactive_keyboard_interrupt(monkeypatch, capsys):
    # Simula input che lancia KeyboardInterrupt
    def raising_input(prompt=''):
        raise KeyboardInterrupt
    monkeypatch.setattr('builtins.input', raising_input)

    main()
    out = capsys.readouterr().out
    assert 'Uscita.' in out
