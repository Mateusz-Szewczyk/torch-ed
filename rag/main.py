# main.py
import os
from document_processor import read_text_file, split_text_into_documents, add_documents_to_vector_store
from vector_store import create_vector_store, load_vector_store, similarity_search
from langchain_community.embeddings import GPT4AllEmbeddings
import subprocess

embedding = GPT4AllEmbeddings()


def run_ollama(model_name, prompt):
    command = ['ollama', 'run', model_name]
    print(f"Running Ollama with model: {model_name} and prompt: {prompt}")

    try:
        result = subprocess.run(command, input=prompt, capture_output=True, text=True, check=True, encoding='utf-8')
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running Ollama: {e}")
        print(f"Standard Output: {e.stdout}")
        print(f"Standard Error: {e.stderr}")
        return ""

def main():
    filename = "python_docs_index.txt"

    if not os.path.exists(filename):
        print(f"File {filename} not found!")
        return

    text = read_text_file(filename)
    documents = split_text_into_documents(text)

    persist_directory = "./chroma_langchain_db_new"

    if not os.path.exists(persist_directory):
        vector_store = create_vector_store(persist_directory=persist_directory)
        add_documents_to_vector_store(vector_store, documents)
    else:
        vector_store = load_vector_store(persist_directory=persist_directory)

    model_name = "llama3.2:3b-instruct-fp16"

    query = "Jak tworzyć oprogramowanie wysokiej jakości?"

    similar_docs = similarity_search(vector_store, query, k=4)
    retrieved_text = "\n\n".join([doc.page_content for doc in similar_docs])
    combined_prompt = f"""
    You are an AI assistant with advanced analytical and communication skills. Your task is to provide accurate, insightful, and tailored responses based on the given information and query.

    Context:
    {retrieved_text}

    Query: {query}

    Response Guidelines:
    1. Analyze: Thoroughly examine the provided context, identifying key concepts, relationships, and relevant details.

    2. Synthesize: Combine insights from multiple sources to form a comprehensive understanding.

    3. Answer: 
       - Begin with a direct, concise answer to the query.
       - Elaborate with supporting details, examples, or explanations as needed.
       - If applicable, present multiple perspectives or interpretations.

    4. Clarity:
       - Use clear, jargon-free language unless technical terms are necessary.
       - Employ bullet points, numbered lists, or short paragraphs for easy readability.

    5. Credibility:
       - Seamlessly incorporate references to the provided context when relevant.
       - Clearly distinguish between information from the context and any inferences or general knowledge you're using.

    6. Completeness:
       - Address all aspects of the query.
       - If the context lacks sufficient information, clearly state this and provide the best possible answer with available data.

    7. Objectivity:
       - Present information impartially, especially for controversial topics.
       - Acknowledge limitations or uncertainties in the data or conclusions.

    8. Engagement:
       - Tailor your tone to suit the nature of the query (e.g., formal for academic questions, conversational for general inquiries).
       - When appropriate, pose thought-provoking questions or suggest areas for further exploration.

    Remember: Start your response directly and avoid repetitive or formulaic introductions. Your goal is to provide a helpful, informative, and engaging answer that directly addresses the user's needs.
    """

    # Run the LLaMA 3.2 3B model via Ollama
    # response = run_ollama(model_name, combined_prompt)
    prompt = """
    Proszę popraw ten tekst zwrócony przez OCR tak aby niepoprawne słowa były poprawione:
    
    Rosdsial 1\nPOJECIA WSTEPNE, NIEROWNOSCI, ROWNANIA MODULOWE\n\n
    § 1.1, POJRCIA WSTEPNE\n\n‘Dutymi literami A, B, C, ... bedziemy oznaczali zbiory, matymi a, b, c, ... elementy\n
    sbioréw. Zapis\naed,\n‘omnacza, 2e element a nalezy do zbioru A, a zapis\naga\n
    te element a nie nalezy do zbioru A. Zapis\nAcB lub B>A\n\n‘
    omnacza, 2e zbidr A jest zawarty w zbiorze B, tzn. kabdy element zbioru A jest elementem\n
    abioru B; méwimy takte wtedy, 2e A jest podzbiorem B lub 2e B jest nadzbiorem A (rys. 1.1).\n
    W szezegélnosci warunek A.< B jest spetniony, gdy zbiory A i B pokrywaia sie (sq identyczne).\n
    Gdy AGB oraz A¥B, to méwimy, te A jest podzbiorem wlasciwym zbioru B.\n\n2\n\nS\n\nAB\nys. Ld\n\n
    Zapis (warunek), w ktérym wystepuia litery (np. x, ys Z5 --), oznaczajace dowolne\n
    liczby nalezace do pewnego zbioru X, a Kt6ry po podstawieniu za te litery jakichkolwick\n
    ticzb naledacych do zbioru X staje sig przy kazdym podstawieniu albo zdaniem prawdziwym\n
    albo zdaniem falszywym (przy rOinych podstawieniach mote byé ré2nie), nazywa si¢\n
    ‘funkejq zdaniowa. Na prayklad zapis x*—4<0 oraz x°+y*=4, gdzie x i y omnaczaja\n
    dowolne liezby rzeczywiste, sa funkejami zdaniowymi\n‘Niech teraz S(x) oznacza pewna funkeje zdaniowa. Woweras zapis\n
    fxexX: SCO}\n\n‘oznacza zbir tych wszystkich liczb x nalezacych do zbioru X, dla ktSrych funkeja zdaniowa\n
    ‘S(x) jest prawdziwa.\n\n'
    """
    response = run_ollama(model_name, prompt)
    # Step 6: Output the final response
    print(f"Generated Response:\n{response}")

if __name__ == "__main__":
    main()


#TODO Przeczytaj o LoRA i Flexora zeby troche finetuningowac model w razie potrzeby