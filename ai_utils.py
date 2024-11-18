# ai_utils.py
from openai import OpenAI
from anthropic import Anthropic
from dotenv import dotenv_values

# Load environment variables from .env file
secrets = dotenv_values(".env")


# API Keys from environment variables
OPENAI_API_KEY = secrets['OPENAI_API']
ANTHROPIC_API_KEY = secrets['ANTHROPIC_API']

# Initialize OpenAI and Anthropic clients
openai_client = OpenAI(api_key= OPENAI_API_KEY)
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

def generate_content_with_claude(prompt, question, answer, template):
    # Use Anthropic's Claude to generate content
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4096,
        system = prompt,
        messages = [
            {"role": "user","content": f"""
                Q: {question}
                A: {answer}

                Template: {template}
            """}
        ],
        
        temperature=1
    )
    return response.content[0].text

def voice_and_brand_edit_with_claude(prompt, question, answer, template, content, brand_voice):
    # Use Anthropic's Claude to generate content
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4096,
        system = prompt,
        messages = [
            {"role": "user","content": f"""
                Q: {question}
                A: {answer}

                Template: {template}
            """},
            {"role":"assistant", "content":content},
            {"role":"user", "content": f"""
                Edit the piece of content by following this client brief and tuning it to their voice and brand guidelines.

                <ClientBrief>
                {brand_voice}
                </ClientBrief>

                """
             }
        ],
        
        temperature=1
    )
    return response.content[0].text


def rewrite_content_to_fit_limit(content, limit=280):
    # Use OpenAI to rewrite content to fit character limit
    prompt = f"""
    ACTION: Your goal is to cut down the provided CONTENT under 280 characters. You are to do this by cutting down fluff and unnecessary words. Eliminate sentences that do not contribute as much to the overall content. You want to retain only the most important details of the CONTENT.

    CONSTRAINT: 
    - Keep the OUTPUT to under {limit} characters. 
    - Keep the sentences simple. 
    - Keep the formatting and template of the original content form.

    CONTENT: {content}
        """
    messages = [
    {'role' : 'system', 'content': prompt},
    {'role' : 'user', 'content': content}
    ]
    response = openai_client.chat.completions.create(
        model = 'gpt-4o-mini-2024-07-18',
        messages = messages,
        max_tokens=4096,
        temperature=0.5,
    )
    return response.choices[0].message.content

def ai_screen_content(content, sample_content):
    # Use Anthropic to screen content for brand voice alignment
    
    messages = [
    {'role' : 'user', 'content': f"Post to review:{content}"}
    ]
    response = anthropic_client.messages.create(
        model = "claude-3-5-sonnet-20241022",
        system = f"""
        You are an expert copy editor tasked with reviewing posts for brand, voice, style, or quality. You will be given a post to review and short form content examples of what success looks like. Your goal is to provide specific, concise feedback on the post.

        Here are the short form examples of successful content:  

        {sample_content}

        When reviewing the post, follow this process:

        1. Carefully read the post and compare it to the short form examples.

        2. Determine if the post meets the standards set by the examples in terms of brand, voice, style, and quality.

        3. Prepare your reasoning for why the post does or does not meet these standards.

        4. If an update is warranted, prepare a suggestion for new copy.

        Provide your review in the following format:

        {{Yes or No}}

        • [Your bullet point reasoning why]

        [If the post is salvageable, provide suggested new copy here] [do not try to save if too far gone]

        Remember to be specific and concise in your feedback. Your review should help improve the post's alignment with the successful short form examples provided.
        """,
        messages = messages,
        max_tokens=4096,
        temperature=0.2,
    )
    #print response to understand what goes on backend
    return response.content[0].text


def generate_content_prompt(brand_voice):
    # Build the prompt for content generation
    prompt = f"""
    You are Crateor, an expert ghostwriter who specializes in writing short-form digital media content. I will give you more details about your "Client", including their writing style, voice, and the topics they write on at the end of these instructions in a "Client Brief".

    Crateor, throughout these instructions I will use "Capitalized Quotes" to identify key terms that we will use to give you more detailed instructions. Take care to remember them.

    The type of content you write fit into 1 category:
    1. "Short Form Social Post" which will be 2-4 sentences of up to 30 words total that make up a short, pithy, and entertaining opinion, story, or short lesson. Make use of line spaces for better structure.

    You operate by following this workflow:
    1. Accept in a Question and Answer pair in the following form alongside a Template to use:

    Q: [Question here]
    A: [Answer to that question]

    Template: [Content Template to follow]

    2. Use the MAIN IDEA of the Question Answer pair to supply the template with information to create the short form content.
    3. Make sure that you provide value to the readers with the output you generate. You aim to inform people.

    Required Output: Short form content that follows the template and contains the information provided by the question answer pair

    WRITING STYLE GUIDELINES:
    - Create novelty with ideas that are counter-intuitive, counter-narrative, shock and awe, or elegantly articulated.
    - Develop supporting points for your argument and discuss the implications (resulting points) of your argument being true.
    - Ensure your ideas resonate by using simple, succinct sentences, examples, counterexamples, persuasive reasoning, curiosity through novel ideas, and resonance through story, analogy, and metaphor.
    - Use direct statements ending in a period.
    - Maintain a casual, conversational tone with 6th-grade level language.
    - Prioritize short, concise sentences.
    - Bias toward short, concise sentences.
    - Format the output using the templates below and ensure the content is relevant to the Client and their chosen Topic.
    - Use short sentences: Online readers tend to skim, so breaking up your content into short sentences and paragraphs makes it easier to read and digest.
    - Avoid buzzwords, jargon, salesy language, or excessive enthusiasm.
    - Do NOT use hashtags (#) or emojis

    CLIENT BRIEF:
    {brand_voice}

    REMINDERS:
    Do NOT UNDER ANY CIRCUMSTANCE produce output with emojis or hashtags
    STICK to the TEMPLATE. Do not deviate much from it.
    """
    return prompt

def compare_brand_voice_and_sample_content(brand_voice, sample_content):
    messages = [
    {'role' : 'user', 'content': f"brand voice:{brand_voice}, content examples: {sample_content}"}
    ]
    response = anthropic_client.messages.create(
        model = "claude-3-5-sonnet-20241022",
        system = f"""
            You are an AI designed to evaluate whether a set of content examples collectively aligns with a specified brand voice. The brand voice will be described as a variable. Your task is to analyze the overall tone, style, and messaging in the content examples and determine if they are consistent with the described brand voice.

            Variables:
            brand voice: A description of the brand's tone, style, values, and key messaging characteristics.
            content examples: A collection of content examples to analyze.

            Output format:
            Alignment: [Yes/No]
            Explanation: [Provide a concise analysis explaining whether the overall content aligns with the brand voice. Highlight the traits of the brand voice observed in the content and any significant deviations.]
            
            """,
        messages = messages,
        max_tokens=4096,
        temperature=0.2,
    )
    #print response to understand what goes on backend
    print(response.content[0].text)
    return response.content[0].text

def main():
    brand_voice = """
    The Client's writing style should be informative, analytical, and ambitious, focusing on entrepreneurship, business strategy, and personal growth. The content should demonstrate a deep understanding of business systems, projects, and operations while emphasizing the importance of adaptability and leveraging technology. The Client values fairness, equal exchange, and repairing cracks in the world, and they appreciate the benefits of competition and embracing unique advantages.

    In terms of tone, the Client prefers an optimistic yet cautious approach, highlighting the significance of strategic partnerships, automation, and a commitment to continuous learning and teaching. To convey complex ideas in an organized manner, the Client's writing should feature concise, direct statements and often incorporate lists.
                    
    """
    with open('sample_content.txt', 'r') as file:
        sample_content = file.read()
    
    #prompt = generate_content_prompt(question, answer, template, brand_voice)
    #content = generate_content_with_claude(prompt)
    content = """
    $100 million by age 40 is a goal for ambitious entrepreneurs. 

    To achieve this, companies must embrace digital transformation:

    Address employee fears about job loss and workload. 
    Position employees as active participants in automation.
    Highlight adaptability and technology use.


    By tackling concerns and ensuring fairness, companies can foster strategic automation partnerships.
    """
    #print(content)
    screened = ai_screen_content(content, sample_content)
    print(screened)
    
    

if __name__ == "__main__":
    main()
