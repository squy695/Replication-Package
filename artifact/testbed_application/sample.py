from flask import Flask, request, jsonify
import numpy as np

app = Flask(__name__)

@app.route('/Interface1', methods=['GET'])
def fft():
    try:
        for i in range(400000):
            i+=1
        return jsonify({f'result': "ok"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/Interface2', methods=['GET'])
def fft2():
    try:
        for i in range(800000):
            i+=1
        return jsonify({f'result': "ok"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/Interface3', methods=['GET'])
def fft3():
    try:
        for i in range(1600000):
            i+=1
        return jsonify({f'result': "ok"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
