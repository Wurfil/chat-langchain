import { MouseEvent } from "react";
import {
  Heading,
  Link,
  Card,
  CardHeader,
  Flex,
  Spacer, Box,
} from "@chakra-ui/react";

export function EmptyState(props: { onChoice: (question: string) => any }) {
  const handleClick = (e: MouseEvent) => {
    props.onChoice((e.target as HTMLDivElement).innerText);
  };
    return (
        <Box className="rounded max-w-full"  display="flex" justifyContent="center">
            <Flex direction="row" justifyContent="center" alignItems="center" gap="4" maxWidth="1400px" >
                {[
                    "Что такое chargeback?",
                    "Почему сумма по возвратам отображается как 0 руб.?",
                    "Что делать, если меняются данные Компании, адрес, реквизиты или email?",
                    "Можно ли создать несколько товаров с одинаковым idо?"
                ].map((question, index) => (
                    <Card
                        key={index}
                        onMouseUp={handleClick}
                        width="180px"
                        height="120px"
                        backgroundColor="rgb(58, 58, 61)"
                        _hover={{ backgroundColor: "rgb(78,78,81)" }}
                        cursor="pointer"
                        justifyContent="center"
                        flexShrink={0}
                    >
                        <CardHeader justifyContent="center" padding="3">
                            <Heading
                                fontSize="xs"
                                fontWeight="medium"
                                color="gray.200"
                                textAlign="center"
                            >
                                {question}
                            </Heading>
                        </CardHeader>
                    </Card>
                ))}
            </Flex>
        </Box>
    );
}
