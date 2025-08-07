# 🛡️ OASM AI Agent Gen Template Nuclei

A chatbot that generates Nuclei templates for penetration testing/network attacks from prompts using three main approaches: AI Agent, RAG, and Fine-tuning. Each approach has its own advantages, disadvantages, and implementation methods that can be combined.

## 🤖 AI Agent

### 💡 Concept

Use LLM as a "virtual programmer" that knows how to generate Nuclei templates, check logic, and even run/validate with actual tools.

### ✅ Advantages

- **Complete workflow automation**: from prompt → code → test → results
- **Multi-tool integration**: Can combine multiple tools (subfinder, httpx, nuclei) in pipeline
- **Flexible and extensible**: Easy to extend to other formats beyond Nuclei
- **Real-time interaction**: Can adjust and optimize templates instantly

### ❌ Disadvantages

- **Complex implementation**: Requires building complex orchestration systems, possibly using LangChain, LlamaIndex, or custom agents
- **Model dependency**: Accuracy depends on model's understanding and how "tool functions" are written
- **High cost**: Requires many API calls and computational resources

### 🎯 When to use

When you want the chatbot to not only generate templates but also actually run tests and optimize templates automatically, like a "pentest copilot".

---

## 🔍 RAG (Retrieval-Augmented Generation)

### 💡 Concept

Separate knowledge about syntax, parameters, and Nuclei template examples into vector DB (ChromaDB, Elasticsearch), so LLM can retrieve before generating results.

### ✅ Advantages

- **Reduce hallucination**: Reduces hallucination because LLM relies on real data
- **Easy updates**: No need to fine-tune model, just update vector DB when new templates arrive
- **Quick deployment**: Relatively simple setup
- **Cost-effective**: Lower cost compared to fine-tuning

### ❌ Disadvantages

- **Data quality dependency**: Model still needs "creativity" based on retrieved data
- **Retrieval performance**: If prompt is too far from examples, results may be weak
- **Context limitations**: Number of retrieved templates limited by context window

### 🎯 When to use

When you have a large repository of Nuclei templates and want the chatbot to generate output that closely follows standard format, avoiding syntax errors.

---

## 🎯 Fine-tune

### 💡 Concept

Teach the model a specialized skill: from security requirements → generate standard Nuclei templates.

### ✅ Advantages

- **High accuracy**: Higher accuracy for specialized tasks
- **Good performance**: No need for RAG if model has learned enough data
- **Deep customization**: Can optimize for organization's specific style and format
- **Low latency**: No time needed to retrieve data

### ❌ Disadvantages

- **High cost**: Requires training data (thousands of templates with descriptions)
- **Long time**: Expensive and time-consuming fine-tuning process
- **Hard to update**: Model difficult to update when new Nuclei versions arrive (need to fine-tune again)
- **Overfitting**: May overfit if data is not diverse enough

### 🎯 When to use

When you have large training data and want the chatbot to generate high-accuracy output, especially for specialized use cases.

---

## 🔄 Combining Approaches

### 🏗️ Hybrid Architecture

```
📝 User prompt
    ↓
🔍 RAG (find related templates from vector DB)
    ↓
🤖 AI Agent → modify / build new template
    ↓
✅ Agent runs nuclei --validate
    ↓
📊 Return results with logs / optimization suggestions
```

## 📋 Additional Components Needed

### 🗄️ Database Schema

- **Templates Collection**: Store templates with metadata
- **Vulnerabilities DB**: Database of vulnerabilities and signatures
- **User Sessions**: Track user interactions and preferences

### 🔐 Security Features

- **Input Validation**: Validate user prompts to prevent injection
- **Rate Limiting**: Limit requests per user
- **Audit Logging**: Log all generated templates
- **Template Sanitization**: Clean templates before execution

### 📊 Monitoring & Analytics

- **Template Success Rate**: Track validation success rate
- **User Feedback Loop**: Collect feedback to improve model
- **Performance Metrics**: Response time, accuracy metrics
- **Usage Analytics**: Most requested vulnerability types

### 🔧 Additional Tools Integration

- **CVE Database**: Automatically update from NVD
- **Shodan API**: Enrich templates with real-world data
- **GitHub Integration**: Pull latest nuclei templates
- **OWASP Integration**: Map with OWASP Top 10
