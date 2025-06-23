from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import folium
import random
import math
import heapq
import os
import json

app = Flask(__name__)

# Tu API Key de Google Maps
API_KEY = "AIzaSyBvQEy2Hkj_mX3-IH0o7mUR9IVB56vn3Cw"

ESTADOS = {
    "Mexico": [23.634501, -102.552784], 
    "Hidalgo": [20.0910963, -98.7623874],
    "Aguascalientes": [21.8852562, -102.2915677], 
    "Baja California": [30.8406338, -115.2837585],
    "Jalisco": [20.6595382, -103.3494376], 
    "Michoacan": [19.5665192, -101.7068294], 
    "Morelos": [18.6813049, -99.1013498], 
    "Chihuahua": [28.6433753, -106.0587908], 
    "Ciudad de Mexico": [19.4326077, -99.133208], 
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

def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos puntos usando la fórmula de Haversine"""
    R = 6371  # Radio de la Tierra en km
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def obtener_ruta(partida, destino, api_key):
    """Obtiene la ruta usando Google Maps API"""
    partida_coords = ESTADOS.get(partida)
    destino_coords = ESTADOS.get(destino)
    
    if not partida_coords or not destino_coords:
        return None, None, None, None
    
    origin = f"{partida_coords[0]},{partida_coords[1]}"
    destination = f"{destino_coords[0]},{destino_coords[1]}"
    
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if data["status"] == "OK" and "routes" in data and len(data["routes"]) > 0:
            route = data["routes"][0]["legs"][0]
            ruta_nombres = [step.get("html_instructions", "Paso") for step in route["steps"]]
            ruta = " → ".join(ruta_nombres)
            distancia = route["distance"]["text"]
            distancia_valor = route["distance"]["value"] / 1000

            return ruta, distancia, distancia_valor, data
        else:
            # Si la API falla, usar cálculo directo
            distancia_km = calcular_distancia_haversine(
                partida_coords[0], partida_coords[1],
                destino_coords[0], destino_coords[1]
            )
            return f"Ruta directa de {partida} a {destino}", f"{distancia_km:.2f} km", distancia_km, None
    except Exception as e:
        print(f"Error en API: {e}")
        # Fallback a cálculo directo
        distancia_km = calcular_distancia_haversine(
            partida_coords[0], partida_coords[1],
            destino_coords[0], destino_coords[1]
        )
        return f"Ruta directa de {partida} a {destino}", f"{distancia_km:.2f} km", distancia_km, None

def obtener_coordenadas(data, partida, destino):
    """Obtiene las coordenadas de la ruta"""
    if data and "routes" in data:
        coordenadas = []
        for step in data["routes"][0]["legs"][0]["steps"]:
            lat, lng = step["start_location"]["lat"], step["start_location"]["lng"]
            coordenadas.append([lat, lng])
        # Agregar el punto final
        lat, lng = data["routes"][0]["legs"][0]["steps"][-1]["end_location"]["lat"], data["routes"][0]["legs"][0]["steps"][-1]["end_location"]["lng"]
        coordenadas.append([lat, lng])
        return coordenadas
    else:
        # Si no hay datos de la API, usar coordenadas directas
        return [ESTADOS[partida], ESTADOS[destino]]

def construir_grafo_estados():
    """Construye un grafo con todos los estados y sus distancias"""
    grafo = {}
    estados_lista = list(ESTADOS.keys())
    
    for i, estado1 in enumerate(estados_lista):
        grafo[estado1] = {}
        coords1 = ESTADOS[estado1]
        
        for j, estado2 in enumerate(estados_lista):
            if i != j:
                coords2 = ESTADOS[estado2]
                distancia = calcular_distancia_haversine(
                    coords1[0], coords1[1], coords2[0], coords2[1]
                )
                grafo[estado1][estado2] = distancia
    
    return grafo

def dijkstra(graph, start, end):
    """Implementación del algoritmo de Dijkstra"""
    distances = {node: float('infinity') for node in graph}
    distances[start] = 0
    priority_queue = [(0, start)]
    previous_nodes = {node: None for node in graph}
    visited = set()

    while priority_queue:
        current_distance, current_node = heapq.heappop(priority_queue)
        
        if current_node in visited:
            continue
            
        visited.add(current_node)

        if current_node == end:
            break

        for neighbor, weight in graph.get(current_node, {}).items():
            distance = current_distance + weight

            if distance < distances.get(neighbor, float('infinity')):
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(priority_queue, (distance, neighbor))

    # Reconstruir el camino
    path = []
    current = end
    while current is not None:
        path.append(current)
        current = previous_nodes[current]
    path.reverse()
    
    return path, distances.get(end, float('infinity'))

def algoritmo_genetico(graph, start, end, population_size=50, generations=100):
    """Algoritmo genético simplificado para encontrar rutas"""
    estados = list(graph.keys())
    
    def crear_individuo():
        # Crear una ruta que incluya start y end
        otros_estados = [e for e in estados if e not in [start, end]]
        # Seleccionar algunos estados intermedios aleatoriamente
        num_intermedios = random.randint(0, min(3, len(otros_estados)))
        intermedios = random.sample(otros_estados, num_intermedios)
        return [start] + intermedios + [end]
    
    def calcular_fitness(individuo):
        distancia_total = 0
        for i in range(len(individuo) - 1):
            distancia_total += graph[individuo[i]].get(individuo[i+1], float('infinity'))
        return distancia_total
    
    # Inicializar población
    poblacion = [crear_individuo() for _ in range(population_size)]
    
    mejor_individuo = min(poblacion, key=calcular_fitness)
    mejor_distancia = calcular_fitness(mejor_individuo)
    
    for generacion in range(generations):
        # Selección y cruce simple
        nueva_poblacion = []
        
        for _ in range(population_size):
            # Seleccionar dos padres aleatorios
            padre1 = random.choice(poblacion)
            padre2 = random.choice(poblacion)
            
            # Cruce simple: tomar elementos únicos de ambos padres
            hijo = [start]
            intermedios = []
            
            for estado in padre1[1:-1] + padre2[1:-1]:
                if estado not in intermedios and estado != start and estado != end:
                    intermedios.append(estado)
            
            # Limitar número de intermedios
            if len(intermedios) > 3:
                intermedios = random.sample(intermedios, 3)
            
            hijo.extend(intermedios)
            hijo.append(end)
            
            # Mutación: cambiar algunos intermedios
            if random.random() < 0.1 and len(hijo) > 2:
                otros_estados = [e for e in estados if e not in hijo]
                if otros_estados:
                    idx = random.randint(1, len(hijo) - 2)
                    hijo[idx] = random.choice(otros_estados)
            
            nueva_poblacion.append(hijo)
        
        poblacion = nueva_poblacion
        
        # Actualizar mejor solución
        candidato = min(poblacion, key=calcular_fitness)
        candidato_distancia = calcular_fitness(candidato)
        
        if candidato_distancia < mejor_distancia:
            mejor_individuo = candidato
            mejor_distancia = candidato_distancia
    
    return mejor_individuo, mejor_distancia

def dibujar_mapa_con_algoritmos(partida, destino, coordenadas, dijkstra_result, genetico_result):
    """Crea un mapa interactivo con las rutas de diferentes algoritmos"""
    # Usar coordenadas de inicio para centrar el mapa
    centro = coordenadas[0] if coordenadas else ESTADOS[partida]
    mapa = folium.Map(location=centro, zoom_start=6)
    
    # Marcadores de inicio y fin
    folium.Marker(
        ESTADOS[partida], 
        popup=f"Inicio: {partida}", 
        icon=folium.Icon(color='red', icon='play')
    ).add_to(mapa)
    
    folium.Marker(
        ESTADOS[destino], 
        popup=f"Destino: {destino}", 
        icon=folium.Icon(color='green', icon='stop')
    ).add_to(mapa)
    
    # Ruta original (si existe)
    if len(coordenadas) > 2:
        folium.PolyLine(
            locations=coordenadas, 
            color='blue', 
            weight=5, 
            opacity=0.7,
            popup="Ruta Google Maps"
        ).add_to(mapa)
    
    # Ruta Dijkstra
    if dijkstra_result and len(dijkstra_result) > 1:
        dijkstra_coords = [ESTADOS[estado] for estado in dijkstra_result]
        folium.PolyLine(
            locations=dijkstra_coords, 
            color='red', 
            weight=3, 
            opacity=0.8,
            popup="Ruta Dijkstra",
            dash_array='10,5'
        ).add_to(mapa)
        
        # Marcadores para estados intermedios de Dijkstra
        for i, estado in enumerate(dijkstra_result[1:-1], 1):
            folium.Marker(
                ESTADOS[estado],
                popup=f"Dijkstra: {estado} (Paso {i})",
                icon=folium.Icon(color='red', icon='info-sign', prefix='glyphicon')
            ).add_to(mapa)
    
    # Ruta Algoritmo Genético
    if genetico_result and len(genetico_result) > 1:
        genetico_coords = [ESTADOS[estado] for estado in genetico_result]
        folium.PolyLine(
            locations=genetico_coords, 
            color='purple', 
            weight=3, 
            opacity=0.8,
            popup="Ruta Algoritmo Genético",
            dash_array='5,10'
        ).add_to(mapa)
        
        # Marcadores para estados intermedios del Algoritmo Genético
        for i, estado in enumerate(genetico_result[1:-1], 1):
            folium.Marker(
                ESTADOS[estado],
                popup=f"Genético: {estado} (Paso {i})",
                icon=folium.Icon(color='purple', icon='info-sign', prefix='glyphicon')
            ).add_to(mapa)
    
    # Guardar mapa
    static_dir = os.path.join(app.root_path, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    ruta_html_path = os.path.join(static_dir, "ruta_interactiva.html")
    mapa.save(ruta_html_path)
    print("Mapa guardado en:", ruta_html_path)
    
    return ruta_html_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ruta', methods=['POST'])
def calcular_ruta():
    try:
        data = request.json
        partida = data.get('partida')
        destino = data.get('destino')

        if not partida or not destino:
            return jsonify({'error': 'Partida y destino son requeridos'}), 400

        if partida == destino:
            return jsonify({'error': 'Partida y destino no pueden ser iguales'}), 400

        print(f"Calculando ruta de {partida} a {destino}")

        # Obtener ruta de Google Maps
        ruta, distancia, distancia_valor, datos_ruta = obtener_ruta(partida, destino, API_KEY)
        
        if ruta is None:
            return jsonify({'error': 'No se pudo calcular la ruta'}), 400

        # Obtener coordenadas
        coordenadas = obtener_coordenadas(datos_ruta, partida, destino)
        
        # Construir grafo de estados
        grafo = construir_grafo_estados()
        
        # Ejecutar algoritmos
        dijkstra_result, dijkstra_distancia = dijkstra(grafo, partida, destino)
        genetico_result, genetico_distancia = algoritmo_genetico(grafo, partida, destino)
        
        # Crear mapa
        dibujar_mapa_con_algoritmos(partida, destino, coordenadas, dijkstra_result, genetico_result)
        
        # Determinar el mejor algoritmo
        algoritmos = [
            {
                "nombre": "Dijkstra", 
                "distancia": dijkstra_distancia, 
                "ruta": dijkstra_result,
                "estados_count": len(dijkstra_result)
            },
            {
                "nombre": "Algoritmo Genético", 
                "distancia": genetico_distancia, 
                "ruta": genetico_result,
                "estados_count": len(genetico_result)
            }
        ]
        
        mejor_algoritmo = min(algoritmos, key=lambda x: x["distancia"])
        
        response = {
            'ruta': ruta,
            'distancia': distancia,
            'algoritmos': algoritmos,
            'mejor_algoritmo': mejor_algoritmo,
            'coordenadas': coordenadas
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error en calcular_ruta: {str(e)}")
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Crear directorio static si no existe
    static_dir = os.path.join(app.root_path, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Crear directorio templates si no existe
    templates_dir = os.path.join(app.root_path, 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
