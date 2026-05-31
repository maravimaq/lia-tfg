import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { Colors } from "@/src/constants/colors";
import { chatService } from "@/src/services/chat";
import {
  ListChatIntent,
  ListChatSuggestion,
  ListChatSuggestionType,
  ListChatStoredMessage,
} from "@/src/types/chat";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: ListChatIntent;
  suggestions?: ListChatSuggestion[];
  isError?: boolean;
};

const QUICK_PROMPTS = [
  "Analiza mi lista",
  "¿Dónde es más barata mi lista?",
  "¿Me recomiendas modificar alguna cantidad?",
  "¿Hay algún producto que pueda cambiar por otro más barato?",
];

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createInitialAssistantMessage(): ChatMessage {
  return {
    id: "initial-assistant-message",
    role: "assistant",
    content:
      "Soy el asistente de esta lista. Puedo analizarla, comparar importes por supermercado, revisar cantidades y detectar posibles ahorros.",
    suggestions: [
      {
        type: "info",
        title: "Consejo",
        description:
          "Prueba con: “Analiza mi lista” o “¿Dónde es más barata mi lista?”.",
      },
    ],
  };
}

function mapStoredMessageToChatMessage(message: ListChatStoredMessage): ChatMessage {
  return {
    id: `stored-${message.id_chat_message}`,
    role: message.role,
    content: message.content,
    intent: message.intent ?? undefined,
    suggestions: message.suggestions ?? [],
  };
}

function getSuggestionStyle(type: ListChatSuggestionType) {
  switch (type) {
    case "warning":
      return {
        container: styles.warningSuggestion,
        title: styles.warningSuggestionTitle,
      };
    case "saving":
    case "substitution":
      return {
        container: styles.savingSuggestion,
        title: styles.savingSuggestionTitle,
      };
    case "quantity":
      return {
        container: styles.quantitySuggestion,
        title: styles.quantitySuggestionTitle,
      };
    case "info":
    default:
      return {
        container: styles.infoSuggestion,
        title: styles.infoSuggestionTitle,
      };
  }
}

function getReadableErrorMessage(error: any) {
  if (error?.code === "ECONNABORTED") {
    return (
      "La IA ha tardado demasiado en responder. Comprueba que Ollama esté iniciado " +
      "y vuelve a intentarlo."
    );
  }

  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") {
    if (detail.toLowerCase().includes("timed out")) {
      return (
        "Ollama ha tardado demasiado en responder. Prueba otra vez o sube " +
        "OLLAMA_TIMEOUT_SECONDS en el .env del backend."
      );
    }

    if (detail.toLowerCase().includes("ollama")) {
      return detail;
    }

    return detail;
  }

  return "No se ha podido consultar el asistente de la lista.";
}

export default function ListaChatbotScreen() {
  const { listaId: listaIdParam, nombreLista } = useLocalSearchParams<{
    listaId: string;
    nombreLista?: string;
  }>();

  const flatListRef = useRef<FlatList<ChatMessage>>(null);

  const listaId = Number(listaIdParam);
  const listaNombre = typeof nombreLista === "string" ? nombreLista : "la lista";

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([
    createInitialAssistantMessage(),
  ]);

  const canSend = useMemo(() => {
    return input.trim().length > 0 && !sending && !loadingHistory && !Number.isNaN(listaId);
  }, [input, listaId, loadingHistory, sending]);

  useEffect(() => {
    let isMounted = true;

    const loadHistory = async () => {
      if (!listaId || Number.isNaN(listaId)) {
        setLoadingHistory(false);
        return;
      }

      try {
        const storedMessages = await chatService.getListMessages(listaId);

        if (!isMounted) {
          return;
        }

        if (storedMessages.length > 0) {
          setMessages(storedMessages.map(mapStoredMessageToChatMessage));
        } else {
          setMessages([createInitialAssistantMessage()]);
        }
      } catch (error) {
        console.error(error);

        if (isMounted) {
          setMessages([
            createInitialAssistantMessage(),
            {
              id: createMessageId(),
              role: "assistant",
              content:
                "No he podido cargar el historial del chat. Puedes seguir usando el asistente igualmente.",
              isError: true,
            },
          ]);
        }
      } finally {
        if (isMounted) {
          setLoadingHistory(false);
          scrollToEnd();
        }
      }
    };

    loadHistory();

    return () => {
      isMounted = false;
    };
  }, [listaId]);

  const scrollToEnd = () => {
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 80);
  };

  const handleSend = async (customMessage?: string) => {
    const text = (customMessage ?? input).trim();

    if (!text || sending) {
      return;
    }

    if (!listaId || Number.isNaN(listaId)) {
      Alert.alert("Error", "No se ha podido identificar la lista.");
      return;
    }

    const userMessage: ChatMessage = {
      id: createMessageId(),
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);
    scrollToEnd();

    try {
      const response = await chatService.sendListMessage(listaId, {
        message: text,
      });

      const assistantMessage: ChatMessage = {
        id: createMessageId(),
        role: "assistant",
        content: response.reply,
        intent: response.intent,
        suggestions: response.suggestions,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error(error);

      const assistantErrorMessage: ChatMessage = {
        id: createMessageId(),
        role: "assistant",
        content: getReadableErrorMessage(error),
        isError: true,
        suggestions: [
          {
            type: "warning",
            title: "Revisa Ollama",
            description:
              "Asegúrate de que Ollama está iniciado y de que el backend tiene configurado OLLAMA_MODEL correctamente.",
          },
        ],
      };

      setMessages((prev) => [...prev, assistantErrorMessage]);
    } finally {
      setSending(false);
      scrollToEnd();
    }
  };

  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isUser = item.role === "user";

    return (
      <View
        style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.assistantBubble,
          item.isError && styles.errorBubble,
        ]}
      >
        <Text
          style={[
            styles.messageText,
            isUser ? styles.userMessageText : styles.assistantMessageText,
          ]}
        >
          {item.content}
        </Text>

        {item.intent ? (
          <View style={styles.intentBadge}>
            <Text style={styles.intentBadgeText}>{item.intent}</Text>
          </View>
        ) : null}

        {item.suggestions && item.suggestions.length > 0 ? (
          <View style={styles.suggestionsBox}>
            {item.suggestions.map((suggestion, index) => {
              const suggestionStyle = getSuggestionStyle(suggestion.type);

              return (
                <View
                  key={`${item.id}-suggestion-${index}`}
                  style={[styles.suggestionCard, suggestionStyle.container]}
                >
                  <Text style={[styles.suggestionTitle, suggestionStyle.title]}>
                    {suggestion.title}
                  </Text>
                  <Text style={styles.suggestionDescription}>
                    {suggestion.description}
                  </Text>
                </View>
              );
            })}
          </View>
        ) : null}
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <Text style={styles.backButtonText}>← Volver</Text>
        </TouchableOpacity>

        <View style={styles.headerCard}>
          <Text style={styles.eyebrow}>Asistente IA</Text>
          <Text style={styles.title}>{listaNombre}</Text>
          <Text style={styles.subtitle}>
            Análisis y recomendaciones sobre esta lista de la compra.
          </Text>
        </View>
      </View>

      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messagesContent}
        onContentSizeChange={scrollToEnd}
        ListFooterComponent={
          loadingHistory || sending ? (
            <View style={[styles.messageBubble, styles.assistantBubble]}>
              <View style={styles.loadingRow}>
                <ActivityIndicator size="small" color={Colors.primary} />
                <Text style={styles.loadingText}>
                  {loadingHistory ? "Cargando historial..." : "LIA está analizando..."}
                </Text>
              </View>
            </View>
          ) : null
        }
      />

      <View style={styles.quickPromptsBox}>
        <FlatList
          horizontal
          data={QUICK_PROMPTS}
          keyExtractor={(item) => item}
          showsHorizontalScrollIndicator={false}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[styles.quickPrompt, (sending || loadingHistory) && styles.disabledElement]}
              onPress={() => handleSend(item)}
              disabled={sending || loadingHistory}
            >
              <Text style={styles.quickPromptText}>{item}</Text>
            </TouchableOpacity>
          )}
        />
      </View>

      <View style={styles.inputBox}>
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder="Pregúntale algo sobre esta lista..."
          placeholderTextColor={Colors.textMuted}
          style={styles.input}
          multiline
          editable={!sending && !loadingHistory}
        />

        <TouchableOpacity
          style={[styles.sendButton, !canSend && styles.disabledElement]}
          onPress={() => handleSend()}
          disabled={!canSend}
        >
          <Text style={styles.sendButtonText}>{sending ? "..." : "Enviar"}</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 10,
  },
  backButton: {
    alignSelf: "flex-start",
    marginBottom: 12,
  },
  backButtonText: {
    color: Colors.title,
    fontSize: 16,
    fontWeight: "900",
  },
  headerCard: {
    backgroundColor: Colors.surface,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: 18,
  },
  eyebrow: {
    color: Colors.primary,
    fontSize: 13,
    fontWeight: "900",
    marginBottom: 4,
    textTransform: "uppercase",
  },
  title: {
    color: Colors.title,
    fontSize: 24,
    fontWeight: "900",
    marginBottom: 6,
  },
  subtitle: {
    color: Colors.textMuted,
    fontSize: 14,
    lineHeight: 20,
  },
  messagesContent: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    gap: 10,
  },
  messageBubble: {
    maxWidth: "88%",
    borderRadius: 18,
    padding: 14,
    borderWidth: 1,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: Colors.surface,
    borderColor: Colors.border,
  },
  errorBubble: {
    backgroundColor: "#FEF2F2",
    borderColor: "#FCA5A5",
  },
  messageText: {
    fontSize: 15,
    lineHeight: 21,
  },
  userMessageText: {
    color: Colors.white,
    fontWeight: "700",
  },
  assistantMessageText: {
    color: Colors.text,
    fontWeight: "600",
  },
  intentBadge: {
    alignSelf: "flex-start",
    marginTop: 10,
    backgroundColor: Colors.backgroundAlt,
    borderRadius: 999,
    paddingVertical: 5,
    paddingHorizontal: 9,
  },
  intentBadgeText: {
    color: Colors.primary,
    fontSize: 11,
    fontWeight: "900",
  },
  suggestionsBox: {
    gap: 8,
    marginTop: 10,
  },
  suggestionCard: {
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
  },
  suggestionTitle: {
    fontSize: 14,
    fontWeight: "900",
    marginBottom: 4,
  },
  suggestionDescription: {
    color: Colors.text,
    fontSize: 13,
    lineHeight: 18,
  },
  infoSuggestion: {
    backgroundColor: Colors.backgroundAlt,
    borderColor: Colors.border,
  },
  infoSuggestionTitle: {
    color: Colors.primary,
  },
  warningSuggestion: {
    backgroundColor: "#FEF3C7",
    borderColor: "#FCD34D",
  },
  warningSuggestionTitle: {
    color: "#92400E",
  },
  savingSuggestion: {
    backgroundColor: "#ECFDF5",
    borderColor: "#86EFAC",
  },
  savingSuggestionTitle: {
    color: "#166534",
  },
  quantitySuggestion: {
    backgroundColor: "#F3E8FF",
    borderColor: "#D8B4FE",
  },
  quantitySuggestionTitle: {
    color: "#6B21A8",
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  loadingText: {
    color: Colors.textMuted,
    fontWeight: "800",
  },
  quickPromptsBox: {
    paddingHorizontal: 20,
    paddingBottom: 10,
  },
  quickPrompt: {
    backgroundColor: Colors.surface,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingVertical: 9,
    paddingHorizontal: 12,
    marginRight: 8,
  },
  quickPromptText: {
    color: Colors.title,
    fontSize: 13,
    fontWeight: "800",
  },
  inputBox: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 18,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.surface,
  },
  input: {
    flex: 1,
    minHeight: 46,
    maxHeight: 110,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.background,
    color: Colors.text,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 15,
  },
  sendButton: {
    minHeight: 46,
    borderRadius: 16,
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
  },
  sendButtonText: {
    color: Colors.white,
    fontWeight: "900",
  },
  disabledElement: {
    opacity: 0.55,
  },
});
