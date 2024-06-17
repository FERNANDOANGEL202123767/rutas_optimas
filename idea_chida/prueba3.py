from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import folium
import random
import math
import heapq
import os

app = Flask(__name__)

API_KEY = "AIzaSyDytpSLPygjIvXWahgD6BABOeMx6VUTQqU"

ESTADOS = {
    "Mexico": [23.634501, -102.552784], 
    "Hidalgo": [20.0910963, -98.7623874],
    "Aguascalientes": [21.8852562, -102.2915677], 
    "Baja California": [30.8406338, -115.2837585],
    "Jalisco": [20.6595382, -103.3494376], 
    "Michoacan": [19.5665192, -101.7068294], 
    "Morelos": [18.6813049, -99.1013498], 
    "Chihuahua": [28.6433753, -106.0587908], 
    "CDMX": [19.4326077, -99.133208], 
    "Nayarit": [21.7513844, -104.8454619], 
    "Guanajuato": [21.0190145, -101.2573586],
    "Guerrero": [17.4391926, -99.54509739999999], 
    "Durango": [24.0248409, -104.6608131],
    "Nuevo Leon": [25.592172, -99.99619469999999], 
    "Campeche": [19.8301251, -90.5349087],
    "Colima": [19.2452342, -103.7240868],
    "Baja California Sur": [26.0444446, -111.6660725],
    "Puebla": [19.0414398, -98.2062727], 
    "Queretaro": [20.5887932, -100.3898881], 
    "Oaxaca": [17.0731842, -96.7265889], 
    "Chiapas": [16.7569318, -93.12923529999999],
    "Quintana Roo": [19.1817393, -88.4791376], 
    "Sinaloa": [25.8226854, -108.2216704], 
    "Yucatan": [20.7098786, -89.0943377],
    "Tlaxcala": [19.318154, -98.2374954],
    "Veracruz": [19.173773, -96.1342241], 
    "Tabasco": [17.8409173, -92.6189273], 
    "Tamaulipas": [24.26694, -98.8362755], 
    "Sonora": [29.2972247, -110.3308814], 
    "Zacatecas": [22.7727913, -102.5765714], 
    "Coahuila": [27.058676, -101.7068294], 
    "San Luis Potosi": [22.1520892, -100.9733024], 
    "Tijuana": [32.5149469, -117.0382471]
}

def obtener_ruta(partida, destino, api_key):
    origin = partida.replace(" ", "+")
    destination = destino.replace(" ", "+")
    
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={api_key}"
    response = requests.get(url)
    data = response.json()

    if data["status"] == "OK" and "routes" in data and len(data["routes"]) > 0:
        route = data["routes"][0]["legs"][0]
        ruta_nombres = [step["html_instructions"] for step in route["steps"]]
        ruta = " → ".join(ruta_nombres)
        distancia = route["distance"]["text"]
        distancia_valor = route["distance"]["value"] / 1000

        return ruta, distancia, distancia_valor, data
    else:
        return None, None, None, None

def obtener_coordenadas(data):
    coordenadas = []
    for step in data["routes"][0]["legs"][0]["steps"]:
        lat, lng = step["start_location"]["lat"], step["start_location"]["lng"]
        coordenadas.append((lat, lng))
    lat, lng = data["routes"][0]["legs"][0]["steps"][-1]["end_location"]["lat"], data["routes"][0]["legs"][0]["steps"][-1]["end_location"]["lng"]
    coordenadas.append((lat, lng))
    return coordenadas

def dibujar_ruta_en_mapa(partida, destino, coordenadas):
    mapa = folium.Map(location=coordenadas[0], zoom_start=10)
    folium.Marker(coordenadas[0], popup="Inicio", icon=folium.Icon(color='red')).add_to(mapa)
    folium.Marker(coordenadas[-1], popup="Destino", icon=folium.Icon(color='green')).add_to(mapa)
    folium.PolyLine(locations=coordenadas, color='blue').add_to(mapa)
    ruta_html_path = os.path.join("static", "ruta_interactiva.html")
    mapa.save(ruta_html_path)
    print("Se ha creado un archivo 'ruta_interactiva.html' con el mapa interactivo.")

def calcular_distancia(coordenadas):
    total_distance = 0
    for i in range(len(coordenadas) - 1):
        lat1, lng1 = coordenadas[i]
        lat2, lng2 = coordenadas[i + 1]
        distance = math.sqrt((lat2 - lat1) ** 2 + (lng2 - lng1) ** 2)
        total_distance += distance
    return total_distance

def dijkstra(graph, initial):
    distances = {node: float('infinity') for node in graph}
    distances[initial] = 0
    priority_queue = [(0, initial)]
    previous_nodes = {node: None for node in graph}

    while priority_queue:
        current_distance, current_node = heapq.heappop(priority_queue)

        if current_distance > distances[current_node]:
            continue

        for neighbor, weight in graph.get(current_node, {}).items():
            distance = current_distance + weight

            if distance < distances.get(neighbor, float('infinity')):
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(priority_queue, (distance, neighbor))

    path = []
    current = max(distances, key=distances.get)
    while current is not None:
        path.append(current)
        current = previous_nodes[current]
    path.reverse()
    return path, distances

def busqueda_tabu(graph, start, end, tabu_size=10, max_iter=100):
    current_solution = [start]
    best_solution = current_solution[:]
    tabu_list = []

    for _ in range(max_iter):
        neighborhood = []
        for node in graph[current_solution[-1]]:
            if node not in tabu_list:
                neighborhood.append(node)
        
        if not neighborhood:
            break

        next_node = random.choice(neighborhood)
        current_solution.append(next_node)

        if next_node == end:
            best_solution = current_solution[:]
            break

        tabu_list.append(next_node)
        if len(tabu_list) > tabu_size:
            tabu_list.pop(0)

    return best_solution

def crossover(parent1, parent2):
    if len(parent1) < 2 or len(parent2) < 2:
        return parent1, parent2
    midpoint = len(parent1) // 2
    child1 = parent1[:midpoint] + parent2[midpoint:]
    child2 = parent2[:midpoint] + parent1[midpoint:]
    return child1, child2

def mutate(individual):
    if len(individual) < 2:
        return individual
    idx1, idx2 = random.sample(range(len(individual)), 2)
    individual[idx1], idx2 = individual[idx2], individual[idx1]
    return individual

def algoritmo_genetico_mejorado(graph, start, end, population_size=100, generations=500, crossover_rate=0.8, mutation_rate=0.02, elitism=True):
    population = [[start] + random.sample(list(graph.keys()), len(graph) - 2) + [end] for _ in range(population_size)]

    def fitness(individual):
        return sum(graph[individual[i]].get(individual[i+1], float('infinity')) for i in range(len(individual) - 1))

    best_individual = min(population, key=fitness)
    best_fitness = fitness(best_individual)

    for generation in range(generations):
        new_population = []

        for _ in range(population_size // 2):
            parent1, parent2 = random.sample(population, 2)
            if random.random() < crossover_rate:
                child1, child2 = crossover(parent1, parent2)
            else:
                child1, child2 = parent1, parent2

            if random.random() < mutation_rate:
                child1 = mutate(child1)
            if random.random() < mutation_rate:
                child2 = mutate(child2)

            new_population.extend([child1, child2])

        if elitism:
            new_population.append(best_individual)

        population = new_population
        current_best = min(population, key=fitness)
        current_best_fitness = fitness(current_best)

        if current_best_fitness < best_fitness:
            best_fitness = current_best_fitness
            best_individual = current_best

    return best_individual, best_fitness

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ruta', methods=['POST'])
def calcular_ruta():
    data = request.json
    partida = data['partida']
    destino = data['destino']

    print("Partida:", partida)
    print("Destino:", destino)

    ruta, distancia, distancia_valor, datos_ruta = obtener_ruta(partida, destino, API_KEY)

    if ruta is not None:
        coordenadas = obtener_coordenadas(datos_ruta)
        dibujar_ruta_en_mapa(partida, destino, coordenadas)

        grafo = construir_grafo(coordenadas)

        dijkstra_result, _ = dijkstra(grafo, 0)
        tabu_result = busqueda_tabu(grafo, 0, len(coordenadas) - 1)
        genetico_result, _ = algoritmo_genetico_mejorado(grafo, 0, len(coordenadas) - 1)

        dijkstra_distancia = calcular_distancia_coordenadas(coordenadas, dijkstra_result)
        tabu_distancia = calcular_distancia_coordenadas(coordenadas, tabu_result)
        genetico_distancia = calcular_distancia_coordenadas(coordenadas, genetico_result)

        rutas = [
            {"nombre": "Dijkstra", "distancia": dijkstra_distancia, "resultados": dijkstra_result},
            {"nombre": "Búsqueda Tabú", "distancia": tabu_distancia, "resultados": tabu_result},
            {"nombre": "Algoritmo Genético", "distancia": genetico_distancia, "resultados": genetico_result}
        ]
        ruta_optima = min(rutas, key=lambda x: x["distancia"])

        return jsonify({
            'ruta': ruta,
            'distancia': distancia,
            'algoritmo_optimo': ruta_optima
        })
    else:
        return jsonify({'error': 'No se encontró una ruta válida para los destinos seleccionados.'}), 400

def construir_grafo(coordenadas):
    graph = {}
    for i, (lat1, lng1) in enumerate(coordenadas):
        graph[i] = {}
        for j, (lat2, lng2) in enumerate(coordenadas):
            if i != j:
                graph[i][j] = math.sqrt((lat2 - lat1) ** 2 + (lng2 - lng1) ** 2)
    return graph

def calcular_distancia_coordenadas(coordenadas, ruta):
    distancia = 0
    for i in range(len(ruta) - 1):
        lat1, lng1 = coordenadas[ruta[i]]
        lat2, lng2 = coordenadas[ruta[i + 1]]
        distancia += math.sqrt((lat2 - lat1) ** 2 + (lng2 - lng1) ** 2)
    return distancia

@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)
