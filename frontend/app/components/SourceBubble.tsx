import React from "react";
import { Card, CardBody, Heading } from "@chakra-ui/react";
import { sendFeedback } from "../utils/sendFeedback";

export type Source = {
    url: string;
    title: string;
};

export function SourceBubble({
                                 source,
                                 highlighted,
                                 onMouseEnter,
                                 onMouseLeave,
                                 runId,
                             }: {
    source: Source;
    highlighted: boolean;
    onMouseEnter: () => any;
    onMouseLeave: () => any;
    runId?: string;
}) {
    // Splitting the title into parts
    const parts = source.title.split(" | ");

    return (
        <Card
            onClick={async () => {
                window.open(source.url, "_blank");
                if (runId) {
                    await sendFeedback({
                        key: "user_click",
                        runId,
                        value: source.url,
                        isExplicit: false,
                    });
                }
            }}
            backgroundColor="white"


            onMouseEnter={onMouseEnter}
            onMouseLeave={onMouseLeave}
            cursor="pointer"
            alignSelf="stretch"
            height="100%"
            overflow="hidden"
        >
            <CardBody>
                <Heading size="sm" fontWeight="normal" color="blue">
                    {parts[0]} {/* Render the first part separately */}
                </Heading>
                {parts.slice(1).join(" | ")} {/* Render all other parts joined together */}
            </CardBody>
        </Card>
    );
}
